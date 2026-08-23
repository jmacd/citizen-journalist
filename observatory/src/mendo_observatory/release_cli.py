"""Command-line interface for immutable corpus releases."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from .release import ReleaseBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-release")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--channel")

    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("--root", type=Path, required=True)
    materialize.add_argument("--destination", type=Path, required=True)
    selection = materialize.add_mutually_exclusive_group(required=True)
    selection.add_argument("--release-id")
    selection.add_argument("--channel")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    builder = ReleaseBuilder(args.root)
    if args.command == "create":
        result = builder.create(channel=args.channel)
        payload = {
            "release_id": result.release.release_id,
            "manifest_path": str(result.manifest_path),
            "manifest_sha256": result.manifest_sha256,
            "channel_path": str(result.channel_path) if result.channel_path else None,
            "event_count": result.release.event_count,
            "record_count": result.release.record_count,
            "object_count": result.release.object_count,
        }
    else:
        result = builder.materialize(
            args.destination,
            release_id=args.release_id,
            channel=args.channel,
        )
        payload = dataclasses.asdict(result)
        payload["destination"] = str(payload["destination"])
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
