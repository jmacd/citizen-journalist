"""Command-line interface for immutable Archive ingestion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .archive import ArchiveStore
from .snapshot import CaptureSnapshotStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-archive")
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("init", help="create an empty archive identity")
    initialize.add_argument("--root", type=Path, required=True)
    initialize.add_argument("--birthplace", required=True)
    initialize.add_argument("--archive-id")
    ingest = subparsers.add_parser("ingest", help="store one original and its event")
    ingest.add_argument("source", type=Path)
    ingest.add_argument("--root", type=Path, required=True)
    ingest.add_argument("--record-id", required=True)
    ingest.add_argument("--title", required=True)
    ingest.add_argument("--collection", action="append", required=True)
    ingest.add_argument("--source-url")
    ingest.add_argument("--custodian")
    ingest.add_argument(
        "--retrieved-at",
        type=datetime.fromisoformat,
        help="original retrieval time as an ISO-8601 timestamp with timezone",
    )
    ingest.add_argument("--media-type")
    snapshot = subparsers.add_parser(
        "snapshot", help="preserve selected workspace paths and restore metadata"
    )
    snapshot.add_argument("--root", type=Path, required=True)
    snapshot.add_argument("--source-root", type=Path, required=True)
    snapshot.add_argument("--source-revision", required=True)
    snapshot.add_argument("--source-label", required=True)
    snapshot.add_argument("--collection", required=True)
    snapshot.add_argument("--include", action="append", required=True)
    snapshot.add_argument("--snapshot-id")
    restore = subparsers.add_parser(
        "restore-snapshot", help="reconstruct a workspace snapshot"
    )
    restore.add_argument("--root", type=Path, required=True)
    restore.add_argument("--snapshot-id", required=True)
    restore.add_argument("--destination", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ArchiveStore(args.root)
    if args.command == "init":
        identity = store.initialize(
            birthplace=args.birthplace,
            archive_id=args.archive_id,
        )
        print(json.dumps(identity.model_dump(mode="json", by_alias=True), sort_keys=True))
        return
    if args.command == "snapshot":
        result = CaptureSnapshotStore(args.root).create(
            args.source_root,
            source_revision=args.source_revision,
            includes=args.include,
            source_label=args.source_label,
            collection=args.collection,
            snapshot_id=args.snapshot_id,
        )
        print(
            json.dumps(
                {
                    "snapshot_id": result.snapshot.snapshot_id,
                    "source_revision": result.snapshot.source_revision,
                    "file_count": result.file_event_count,
                    "object_created_count": result.object_created_count,
                    "manifest_sha256": result.manifest_sha256,
                    "manifest_object_path": str(result.manifest_object_path),
                },
                sort_keys=True,
            )
        )
        return
    if args.command == "restore-snapshot":
        result = CaptureSnapshotStore(args.root).restore(
            args.snapshot_id,
            args.destination,
        )
        print(
            json.dumps(
                {
                    "snapshot_id": result.snapshot_id,
                    "destination": str(result.destination),
                    "restored_file_count": result.restored_file_count,
                    "restored_bytes": result.restored_bytes,
                },
                sort_keys=True,
            )
        )
        return
    result = store.ingest_file(
        args.source,
        record_id=args.record_id,
        record_title=args.title,
        collections=args.collection,
        source_url=args.source_url,
        custodian=args.custodian,
        retrieved_at=args.retrieved_at,
        media_type=args.media_type,
    )
    print(
        json.dumps(
            {
                "event_id": result.event.event_id,
                "sha256": result.event.object.sha256,
                "object_created": result.object_created,
                "object_path": str(result.object_path),
                "event_path": str(result.event_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
