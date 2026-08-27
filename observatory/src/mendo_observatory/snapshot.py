"""Verified capture-tree snapshots over the immutable Observatory Archive."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .archive import ArchiveStore
from .contracts import CaptureSnapshot, CaptureSnapshotEntry
from .corpus import CorpusBuilder
from .errors import ArchiveWriteError, IntegrityError


@dataclass(frozen=True)
class SnapshotResult:
    snapshot: CaptureSnapshot
    manifest_sha256: str
    manifest_object_path: Path
    file_event_count: int
    object_created_count: int


@dataclass(frozen=True)
class RestoreResult:
    snapshot_id: str
    destination: Path
    restored_file_count: int
    restored_bytes: int


class CaptureSnapshotStore:
    def __init__(self, archive_root: Path) -> None:
        self.archive = ArchiveStore(
            archive_root,
            producer_name="mendo-capture-snapshot",
        )
        self.root = self.archive.root

    def create(
        self,
        source_root: Path,
        *,
        source_revision: str,
        includes: list[str],
        source_label: str,
        collection: str,
        snapshot_id: str | None = None,
    ) -> SnapshotResult:
        self.archive.load_identity()
        source_root = source_root.resolve(strict=True)
        canonical_snapshot_id = self._snapshot_id(snapshot_id)
        record_id = f"capture-snapshot:{canonical_snapshot_id}"
        if any(
            event.record_id == record_id
            for event in CorpusBuilder(self.root).load_events()
        ):
            raise ArchiveWriteError(
                f"capture snapshot already exists: {canonical_snapshot_id}"
            )
        files = self._included_files(source_root, includes)
        entries: list[CaptureSnapshotEntry] = []
        created_count = 0
        with tempfile.TemporaryDirectory(prefix="mendo-capture-snapshot-") as temp:
            temporary_root = Path(temp)
            for relative, source in files:
                ingest_source = source
                if source.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
                    ingest_source = temporary_root / relative
                    ingest_source.parent.mkdir(parents=True, exist_ok=True)
                    self._backup_sqlite(source, ingest_source)
                metadata = source.stat()
                record_hash = hashlib.sha256(
                    relative.as_posix().encode("utf-8")
                ).hexdigest()[:32]
                result = self.archive.ingest_file(
                    ingest_source,
                    record_id=f"workspace-file:{record_hash}",
                    record_title=relative.as_posix(),
                    collections=[collection, "workspace-capture"],
                    custodian=source_label,
                    retrieved_at=datetime.fromtimestamp(
                        metadata.st_mtime, tz=UTC
                    ),
                )
                created_count += int(result.object_created)
                entries.append(
                    CaptureSnapshotEntry(
                        path=relative.as_posix(),
                        sha256=result.event.object.sha256,
                        bytes=result.event.object.bytes,
                        mode=stat.S_IMODE(metadata.st_mode),
                        modified_at=datetime.fromtimestamp(
                            metadata.st_mtime, tz=UTC
                        ),
                    )
                )

            snapshot = CaptureSnapshot(
                snapshot_id=canonical_snapshot_id,
                created_at=datetime.now(UTC),
                source_revision=source_revision,
                source_label=source_label,
                includes=includes,
                entries=entries,
            )
            manifest_path = temporary_root / f"{canonical_snapshot_id}.json"
            manifest_path.write_text(
                json.dumps(
                    snapshot.model_dump(mode="json", by_alias=True),
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = self.archive.ingest_file(
                manifest_path,
                record_id=record_id,
                record_title=f"Capture snapshot {canonical_snapshot_id}",
                collections=[collection, "workspace-snapshots"],
                custodian=source_label,
                media_type="application/json",
            )
        return SnapshotResult(
            snapshot=snapshot,
            manifest_sha256=manifest.event.object.sha256,
            manifest_object_path=manifest.object_path,
            file_event_count=len(entries),
            object_created_count=created_count + int(manifest.object_created),
        )

    def load(self, snapshot_id: str) -> CaptureSnapshot:
        canonical_snapshot_id = self._snapshot_id(snapshot_id)
        record_id = f"capture-snapshot:{canonical_snapshot_id}"
        events = CorpusBuilder(self.root).load_events()
        matches = [event for event in events if event.record_id == record_id]
        if len(matches) != 1:
            raise IntegrityError(
                f"expected one manifest event for snapshot "
                f"{canonical_snapshot_id}, found {len(matches)}"
            )
        path = self.root / matches[0].object.archive_path
        try:
            return CaptureSnapshot.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as error:
            raise IntegrityError(
                f"capture snapshot manifest is invalid: {path}: {error}"
            ) from error

    def restore(
        self,
        snapshot_id: str,
        destination: Path,
    ) -> RestoreResult:
        snapshot = self.load(snapshot_id)
        destination = destination.resolve()
        if destination.exists():
            raise ArchiveWriteError(
                f"snapshot destination already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{snapshot.snapshot_id}.tmp"
        )
        if temporary.exists():
            raise ArchiveWriteError(
                f"snapshot restore temporary path already exists: {temporary}"
            )
        restored_bytes = 0
        try:
            temporary.mkdir(mode=0o750)
            for entry in snapshot.entries:
                source = (
                    self.root
                    / "objects"
                    / "sha256"
                    / entry.sha256[:2]
                    / entry.sha256
                )
                target = temporary / entry.path
                target.parent.mkdir(parents=True, exist_ok=True)
                self._copy_verified(source, target, entry)
                restored_bytes += entry.bytes
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return RestoreResult(
            snapshot_id=snapshot.snapshot_id,
            destination=destination,
            restored_file_count=len(snapshot.entries),
            restored_bytes=restored_bytes,
        )

    @staticmethod
    def _snapshot_id(value: str | None) -> str:
        if value is None:
            return str(uuid.uuid4())
        try:
            canonical = str(uuid.UUID(value))
        except ValueError as error:
            raise ArchiveWriteError(f"invalid snapshot ID: {value!r}") from error
        if canonical != value:
            raise ArchiveWriteError(
                f"snapshot ID is not canonical: {value!r}"
            )
        return canonical

    @staticmethod
    def _included_files(
        source_root: Path, includes: list[str]
    ) -> list[tuple[PurePosixPath, Path]]:
        if not includes:
            raise ArchiveWriteError("at least one include path is required")
        files: dict[str, Path] = {}
        for raw in includes:
            relative = PurePosixPath(raw)
            if (
                not raw
                or relative.is_absolute()
                or ".." in relative.parts
                or "." in relative.parts
                or relative.as_posix() != raw
            ):
                raise ArchiveWriteError(
                    f"include path is not a safe relative path: {raw!r}"
                )
            candidate = (source_root / relative).resolve(strict=True)
            try:
                candidate.relative_to(source_root)
            except ValueError as error:
                raise ArchiveWriteError(
                    f"include path escapes source root: {raw!r}"
                ) from error
            paths = [candidate] if candidate.is_file() else sorted(
                path for path in candidate.rglob("*") if path.is_file()
            )
            for path in paths:
                if path.is_symlink():
                    raise ArchiveWriteError(
                        f"snapshot input must not contain symlinks: {path}"
                    )
                relative_path = path.relative_to(source_root).as_posix()
                files[relative_path] = path
        return [
            (PurePosixPath(relative), files[relative])
            for relative in sorted(files)
        ]

    @staticmethod
    def _backup_sqlite(source: Path, destination: Path) -> None:
        try:
            source_uri = f"file:{source.as_posix()}?mode=ro"
            with sqlite3.connect(source_uri, uri=True) as input_database:
                with sqlite3.connect(destination) as output_database:
                    input_database.backup(output_database)
                    result = output_database.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()
                    if result is None or result[0] != "ok":
                        raise IntegrityError(
                            f"SQLite backup failed integrity check: {source}"
                        )
        except sqlite3.Error as error:
            raise IntegrityError(
                f"cannot create consistent SQLite backup of {source}: {error}"
            ) from error

    @staticmethod
    def _copy_verified(
        source: Path,
        destination: Path,
        entry: CaptureSnapshotEntry,
    ) -> None:
        digest = hashlib.sha256()
        byte_count = 0
        try:
            with source.open("rb") as input_stream, destination.open(
                "xb"
            ) as output_stream:
                while chunk := input_stream.read(1024 * 1024):
                    output_stream.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
                output_stream.flush()
                os.fsync(output_stream.fileno())
            os.chmod(destination, entry.mode)
        except OSError as error:
            raise IntegrityError(
                f"cannot restore archived object {source}: {error}"
            ) from error
        if byte_count != entry.bytes or digest.hexdigest() != entry.sha256:
            raise IntegrityError(
                f"restored object failed verification: {destination}"
            )
