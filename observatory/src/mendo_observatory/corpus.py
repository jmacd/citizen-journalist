"""Replay Archive events into rebuildable global Parquet catalogs."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from .contracts import ArchiveIdentity, ObjectStoredEvent
from .errors import IntegrityError, InvalidEventError
from .storage import BUFFER_SIZE


CATALOG_SCHEMAS: dict[str, pa.Schema] = {
    "records": pa.schema(
        [
            ("record_id", pa.string()),
            ("title", pa.string()),
            ("title_event_id", pa.string()),
        ]
    ),
    "objects": pa.schema(
        [
            ("sha256", pa.string()),
            ("bytes", pa.int64()),
            ("media_type", pa.string()),
            ("archive_path", pa.string()),
            ("metadata_event_id", pa.string()),
        ]
    ),
    "renditions": pa.schema(
        [
            ("rendition_id", pa.string()),
            ("record_id", pa.string()),
            ("sha256", pa.string()),
            ("kind", pa.string()),
            ("original_filename", pa.string()),
            ("metadata_event_id", pa.string()),
        ]
    ),
    "provenance-events": pa.schema(
        [
            ("event_id", pa.string()),
            ("event_type", pa.string()),
            ("occurred_at", pa.timestamp("us", tz="UTC")),
            ("record_id", pa.string()),
            ("sha256", pa.string()),
            ("media_type", pa.string()),
            ("original_filename", pa.string()),
            ("source_url", pa.string()),
            ("custodian", pa.string()),
            ("retrieved_at", pa.timestamp("us", tz="UTC")),
            ("producer_name", pa.string()),
            ("producer_version", pa.string()),
        ]
    ),
    "relationships": pa.schema(
        [
            ("relationship_id", pa.string()),
            ("from_record_id", pa.string()),
            ("to_record_id", pa.string()),
            ("kind", pa.string()),
            ("event_id", pa.string()),
        ]
    ),
    "collection-memberships": pa.schema(
        [
            ("collection_id", pa.string()),
            ("record_id", pa.string()),
            ("event_id", pa.string()),
        ]
    ),
}


@dataclass(frozen=True)
class BuildResult:
    event_count: int
    record_count: int
    object_count: int
    catalog_paths: dict[str, Path]


@dataclass(frozen=True)
class VerificationReport:
    event_count: int
    object_count: int
    verified_bytes: int


class CorpusBuilder:
    def __init__(self, archive_root: Path) -> None:
        self.root = archive_root.resolve()

    def load_identity(self) -> ArchiveIdentity:
        path = self.root / "archive.json"
        try:
            return ArchiveIdentity.model_validate_json(path.read_bytes())
        except (OSError, ValidationError, ValueError) as error:
            raise InvalidEventError(
                f"archive is not initialized or its identity is invalid: {path}: {error}"
            ) from error

    def load_events(self) -> list[ObjectStoredEvent]:
        self.load_identity()
        event_root = self.root / "events"
        object_root = self.root / "objects" / "sha256"
        if not event_root.is_dir():
            raise InvalidEventError(f"archive event directory does not exist: {event_root}")
        if not object_root.is_dir():
            raise IntegrityError(f"archive object directory does not exist: {object_root}")
        events: list[ObjectStoredEvent] = []
        seen_event_ids: set[str] = set()
        for path in sorted(event_root.glob("*/*.json")):
            try:
                event = ObjectStoredEvent.model_validate_json(path.read_bytes())
            except (OSError, ValidationError, ValueError) as error:
                raise InvalidEventError(f"invalid event {path}: {error}") from error
            if event.event_id in seen_event_ids:
                raise InvalidEventError(f"duplicate event ID: {event.event_id}")
            seen_event_ids.add(event.event_id)
            events.append(event)
        return sorted(events, key=lambda event: (event.occurred_at, event.event_id))

    def verify(
        self, events: list[ObjectStoredEvent] | None = None
    ) -> VerificationReport:
        events = events if events is not None else self.load_events()
        objects: dict[str, tuple[Path, int]] = {}
        for event in events:
            path = self.root / event.object.archive_path
            prior = objects.get(event.object.sha256)
            if prior is not None and prior != (path, event.object.bytes):
                raise IntegrityError(
                    f"object metadata conflicts for SHA-256 {event.object.sha256}"
                )
            objects[event.object.sha256] = (path, event.object.bytes)

        verified_bytes = 0
        for digest, (path, expected_bytes) in sorted(objects.items()):
            actual_digest = hashlib.sha256()
            actual_bytes = 0
            try:
                with path.open("rb") as source:
                    while chunk := source.read(BUFFER_SIZE):
                        actual_digest.update(chunk)
                        actual_bytes += len(chunk)
            except OSError as error:
                raise IntegrityError(f"cannot read archived object {path}: {error}") from error
            if actual_bytes != expected_bytes or actual_digest.hexdigest() != digest:
                raise IntegrityError(f"archived object failed verification: {path}")
            verified_bytes += actual_bytes

        referenced_paths = {path for path, _ in objects.values()}
        object_root = self.root / "objects" / "sha256"
        archived_paths = {
            path for path in object_root.glob("*/*") if path.is_file()
        }
        orphaned = sorted(archived_paths - referenced_paths)
        if orphaned:
            sample = ", ".join(str(path) for path in orphaned[:3])
            raise IntegrityError(
                f"archive contains {len(orphaned)} unreferenced object(s): {sample}"
            )

        return VerificationReport(
            event_count=len(events),
            object_count=len(objects),
            verified_bytes=verified_bytes,
        )

    def build_catalogs(self, *, allow_empty: bool = False) -> BuildResult:
        events = self.load_events()
        if not events and not allow_empty:
            raise InvalidEventError(
                "archive has no finalized events; pass allow_empty=True explicitly "
                "to create empty catalogs"
            )
        self.verify(events)
        rows = self._catalog_rows(events)
        catalog_directory = self.root / "catalog"
        catalog_directory.mkdir(parents=True, exist_ok=True)

        paths: dict[str, Path] = {}
        for name, schema in CATALOG_SCHEMAS.items():
            table = pa.Table.from_pylist(rows[name], schema=schema)
            path = catalog_directory / f"{name}.parquet"
            self._write_parquet_atomic(table, path)
            paths[name] = path

        return BuildResult(
            event_count=len(events),
            record_count=len(rows["records"]),
            object_count=len(rows["objects"]),
            catalog_paths=paths,
        )

    def _catalog_rows(
        self, events: list[ObjectStoredEvent]
    ) -> dict[str, list[dict[str, object]]]:
        records: dict[str, dict[str, object]] = {}
        objects: dict[str, dict[str, object]] = {}
        renditions: dict[str, dict[str, object]] = {}
        provenance: list[dict[str, object]] = []
        memberships: set[tuple[str, str, str]] = set()

        for event in events:
            existing_record = records.get(event.record_id)
            record_row = {
                "record_id": event.record_id,
                "title": event.record_title,
                "title_event_id": event.event_id,
            }
            records[event.record_id] = record_row

            object_row = {
                "sha256": event.object.sha256,
                "bytes": event.object.bytes,
                "media_type": event.object.media_type,
                "archive_path": event.object.archive_path,
                "metadata_event_id": event.event_id,
            }
            prior_object = objects.get(event.object.sha256)
            if prior_object is not None and (
                prior_object["bytes"] != object_row["bytes"]
                or prior_object["archive_path"] != object_row["archive_path"]
            ):
                raise InvalidEventError(
                    f"object {event.object.sha256} has conflicting metadata"
                )
            objects[event.object.sha256] = object_row

            rendition_id = f"{event.record_id}:original:{event.object.sha256}"
            renditions[rendition_id] = {
                "rendition_id": rendition_id,
                "record_id": event.record_id,
                "sha256": event.object.sha256,
                "kind": "original",
                "original_filename": event.object.original_filename,
                "metadata_event_id": event.event_id,
            }
            provenance.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at,
                    "record_id": event.record_id,
                    "sha256": event.object.sha256,
                    "media_type": event.object.media_type,
                    "original_filename": event.object.original_filename,
                    "source_url": event.source.url,
                    "custodian": event.source.custodian,
                    "retrieved_at": event.source.retrieved_at,
                    "producer_name": event.producer.name,
                    "producer_version": event.producer.version,
                }
            )
            memberships.update(
                (collection, event.record_id, event.event_id)
                for collection in event.collections
            )

        return {
            "records": [records[key] for key in sorted(records)],
            "objects": [objects[key] for key in sorted(objects)],
            "renditions": [renditions[key] for key in sorted(renditions)],
            "provenance-events": sorted(provenance, key=lambda row: str(row["event_id"])),
            "relationships": [],
            "collection-memberships": [
                {
                    "collection_id": collection,
                    "record_id": record_id,
                    "event_id": event_id,
                }
                for collection, record_id, event_id in sorted(memberships)
            ],
        }

    @staticmethod
    def _write_parquet_atomic(table: pa.Table, path: Path) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        os.fchmod(descriptor, 0o640)
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            pq.write_table(table, temporary_path, compression="zstd")
            with temporary_path.open("r+b") as source:
                os.fsync(source.fileno())
            os.replace(temporary_path, path)
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            temporary_path.unlink(missing_ok=True)
