"""Command-line interface for corpus replay and verification."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from .corpus import CorpusBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-corpus")
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="permit build to create empty catalogs for an initialized empty archive",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    builder = CorpusBuilder(args.root)
    result = (
        builder.build_catalogs(allow_empty=args.allow_empty)
        if args.command == "build"
        else builder.verify()
    )
    payload = dataclasses.asdict(result)
    if "catalog_paths" in payload:
        payload["catalog_paths"] = {
            name: str(path) for name, path in payload["catalog_paths"].items()
        }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
