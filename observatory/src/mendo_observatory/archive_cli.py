"""Command-line interface for immutable Archive ingestion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .archive import ArchiveStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-archive")
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("init", help="create an empty archive identity")
    initialize.add_argument("--root", type=Path, required=True)
    initialize.add_argument("--birthplace", required=True)
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
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = ArchiveStore(args.root)
    if args.command == "init":
        identity = store.initialize(birthplace=args.birthplace)
        print(json.dumps(identity.model_dump(mode="json", by_alias=True), sort_keys=True))
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
