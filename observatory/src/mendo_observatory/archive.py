"""NFS-compatible immutable object and event writer."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contracts import (
    ArchiveIdentity,
    IngestMetadata,
    ObjectStoredEvent,
    Producer,
    SourceProvenance,
    StoredObject,
    utc_now,
)
from .errors import ArchiveWriteError, IntegrityError
from .storage import (
    BUFFER_SIZE,
    ensure_directory,
    install_create_only,
    sync_directory,
    write_create_only,
)


@dataclass(frozen=True)
class IngestResult:
    event: ObjectStoredEvent
    object_path: Path
    event_path: Path
    object_created: bool


class ArchiveStore:
    """Write immutable objects and finalized event files beneath one root."""

    def __init__(
        self,
        root: Path,
        *,
        producer_name: str = "mendo-archive",
        producer_version: str = "0.1.0",
        file_mode: int = 0o640,
    ) -> None:
        self.root = root.resolve()
        self.producer = Producer(name=producer_name, version=producer_version)
        self.file_mode = file_mode

    def initialize(
        self,
        *,
        birthplace: str,
        archive_id: str | None = None,
    ) -> ArchiveIdentity:
        if archive_id is not None:
            try:
                canonical_archive_id = str(uuid.UUID(archive_id))
            except ValueError as error:
                raise ArchiveWriteError(
                    f"invalid archive ID: {archive_id!r}"
                ) from error
            if canonical_archive_id != archive_id:
                raise ArchiveWriteError(
                    f"archive ID is not canonical: {archive_id!r}"
                )
        for relative in ("objects/sha256", "events", "envelopes", "exports"):
            ensure_directory(self.root / relative)
        identity_path = self.root / "archive.json"
        if identity_path.exists():
            identity = self.load_identity()
            if identity.birthplace != birthplace:
                raise ArchiveWriteError(
                    f"archive birthplace is {identity.birthplace!r}, not {birthplace!r}"
                )
            if archive_id is not None and identity.archive_id != archive_id:
                raise ArchiveWriteError(
                    f"archive ID is {identity.archive_id!r}, not {archive_id!r}"
                )
            return identity

        identity = ArchiveIdentity(
            archive_id=archive_id or str(uuid.uuid4()),
            birthplace=birthplace,
            created_at=utc_now(),
        )
        payload = (
            json.dumps(
                identity.model_dump(mode="json", by_alias=True),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        write_create_only(identity_path, payload, file_mode=self.file_mode)
        return identity

    def load_identity(self) -> ArchiveIdentity:
        identity_path = self.root / "archive.json"
        try:
            return ArchiveIdentity.model_validate_json(identity_path.read_bytes())
        except (OSError, ValueError) as error:
            raise ArchiveWriteError(
                f"archive is not initialized or its identity is invalid: {identity_path}: "
                f"{error}"
            ) from error

    def ingest_file(
        self,
        source_path: Path,
        *,
        record_id: str,
        record_title: str,
        collections: list[str],
        source_url: str | None = None,
        custodian: str | None = None,
        retrieved_at: datetime | None = None,
        media_type: str | None = None,
    ) -> IngestResult:
        source_path = source_path.resolve(strict=True)
        if not source_path.is_file():
            raise ArchiveWriteError(f"source is not a regular file: {source_path}")
        self.load_identity()
        now = utc_now()
        metadata = IngestMetadata(
            record_id=record_id,
            record_title=record_title,
            collections=collections,
            source_url=source_url,
            custodian=custodian,
            retrieved_at=retrieved_at or now,
            media_type=media_type,
        )

        digest, byte_count, temporary_path = self._stage_object(source_path)
        relative_object_path = Path("objects") / "sha256" / digest[:2] / digest
        object_path = self.root / relative_object_path
        ensure_directory(object_path.parent)

        try:
            object_created = install_create_only(temporary_path, object_path)
            if not object_created:
                self._verify_existing_object(object_path, digest, byte_count)
        except IntegrityError:
            quarantine = self.root / "objects" / ".quarantine"
            ensure_directory(quarantine)
            quarantine_path = quarantine / f"{digest}-{uuid.uuid4()}"
            os.replace(temporary_path, quarantine_path)
            sync_directory(quarantine)
            raise IntegrityError(
                f"existing object {object_path} is corrupt; staged bytes retained at "
                f"{quarantine_path}"
            )
        finally:
            temporary_path.unlink(missing_ok=True)

        event = ObjectStoredEvent(
            event_id=str(uuid.uuid4()),
            occurred_at=now,
            record_id=metadata.record_id,
            record_title=metadata.record_title,
            collections=metadata.collections,
            object=StoredObject(
                sha256=digest,
                bytes=byte_count,
                media_type=metadata.media_type
                or mimetypes.guess_type(source_path.name)[0]
                or "application/octet-stream",
                original_filename=source_path.name,
                archive_path=relative_object_path.as_posix(),
            ),
            source=SourceProvenance(
                url=metadata.source_url,
                custodian=metadata.custodian,
                retrieved_at=metadata.retrieved_at,
            ),
            producer=self.producer,
        )
        event_path = self._write_event(event)
        return IngestResult(
            event=event,
            object_path=object_path,
            event_path=event_path,
            object_created=object_created,
        )

    def _stage_object(self, source_path: Path) -> tuple[str, int, Path]:
        staging_dir = self.root / "objects" / ".staging"
        ensure_directory(staging_dir)
        descriptor, temporary_name = tempfile.mkstemp(prefix="object-", dir=staging_dir)
        digest = hashlib.sha256()
        byte_count = 0
        try:
            with os.fdopen(descriptor, "wb") as destination, source_path.open("rb") as source:
                os.fchmod(destination.fileno(), self.file_mode)
                while chunk := source.read(BUFFER_SIZE):
                    destination.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
                destination.flush()
                os.fsync(destination.fileno())
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
        return digest.hexdigest(), byte_count, Path(temporary_name)

    def _verify_existing_object(
        self, object_path: Path, expected_digest: str, expected_bytes: int
    ) -> None:
        actual_digest = hashlib.sha256()
        actual_bytes = 0
        with object_path.open("rb") as source:
            while chunk := source.read(BUFFER_SIZE):
                actual_digest.update(chunk)
                actual_bytes += len(chunk)
        if actual_bytes != expected_bytes or actual_digest.hexdigest() != expected_digest:
            raise IntegrityError(
                f"existing archive object does not match its path: {object_path}"
            )

    def _write_event(self, event: ObjectStoredEvent) -> Path:
        event_directory = self.root / "events" / event.occurred_at.strftime("%Y-%m-%d")
        ensure_directory(event_directory)
        event_path = event_directory / f"{event.event_id}.json"
        payload = (
            json.dumps(
                event.model_dump(mode="json", by_alias=True),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        write_create_only(event_path, payload, file_mode=self.file_mode)
        return event_path
