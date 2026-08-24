"""Command-line interface for immutable corpus releases."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path

from .errors import InvalidEventError
from .remote import S3ReleaseStore
from .receipt import create_staging_receipt, sign_staging_receipt
from .release import ReleaseBuilder
from .release import serialize_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-release")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--channel")
    create.add_argument(
        "--reuse-unchanged",
        action="store_true",
        help="reuse the current channel release when verified corpus content is unchanged",
    )

    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("--root", type=Path, required=True)
    materialize.add_argument("--destination", type=Path, required=True)
    selection = materialize.add_mutually_exclusive_group(required=True)
    selection.add_argument("--release-id")
    selection.add_argument("--channel")

    push = subparsers.add_parser("push-s3")
    push.add_argument("--root", type=Path, required=True)
    add_s3_arguments(push)
    push_selection = push.add_mutually_exclusive_group(required=True)
    push_selection.add_argument("--release-id")
    push_selection.add_argument("--channel")
    push.add_argument(
        "--verify-reused",
        action="store_true",
        help="download and hash remote immutable keys that would otherwise be reused",
    )

    ensure_bucket = subparsers.add_parser("ensure-s3-bucket")
    add_s3_arguments(ensure_bucket)

    pull = subparsers.add_parser("materialize-s3")
    pull.add_argument("--destination", type=Path, required=True)
    pull.add_argument("--archive-id", required=True)
    add_s3_arguments(pull)
    pull_selection = pull.add_mutually_exclusive_group(required=True)
    pull_selection.add_argument("--release-id")
    pull_selection.add_argument("--channel")
    pull.add_argument(
        "--expected-manifest-sha256",
        help="required integrity anchor when materializing by release ID",
    )

    receipt = subparsers.add_parser("receipt")
    receipt.add_argument("--materialized-root", type=Path, required=True)
    receipt.add_argument("--materialized-path", required=True)
    receipt.add_argument("--source-revision", required=True)
    receipt.add_argument("--source-sha256", required=True)
    receipt.add_argument("--runtime-lock-sha256", required=True)
    receipt.add_argument("--python-version", required=True)
    receipt.add_argument("--channel", required=True)
    receipt.add_argument("--expected-archive-id", required=True)
    receipt.add_argument("--expected-release-id", required=True)
    receipt.add_argument("--expected-manifest-sha256", required=True)
    return parser


def add_s3_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--endpoint-url")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--prefix", default="")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "create":
        builder = ReleaseBuilder(args.root)
        result = builder.create(
            channel=args.channel,
            reuse_unchanged=args.reuse_unchanged,
        )
        payload = {
            "release_id": result.release.release_id,
            "manifest_path": str(result.manifest_path),
            "manifest_sha256": result.manifest_sha256,
            "channel_path": str(result.channel_path) if result.channel_path else None,
            "event_count": result.release.event_count,
            "record_count": result.release.record_count,
            "object_count": result.release.object_count,
            "reused": result.reused,
        }
    elif args.command == "materialize":
        builder = ReleaseBuilder(args.root)
        result = builder.materialize(
            args.destination,
            release_id=args.release_id,
            channel=args.channel,
        )
        payload = dataclasses.asdict(result)
        payload["destination"] = str(payload["destination"])
    elif args.command == "push-s3":
        store = S3ReleaseStore.from_boto3(
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            prefix=args.prefix,
        )
        result = store.push(
            ReleaseBuilder(args.root),
            release_id=args.release_id,
            channel=args.channel,
            verify_reused=args.verify_reused,
        )
        payload = dataclasses.asdict(result)
    elif args.command == "ensure-s3-bucket":
        store = S3ReleaseStore.from_boto3(
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            prefix=args.prefix,
        )
        payload = {
            "bucket": args.bucket,
            "created": store.ensure_bucket(region_name=args.region),
        }
    elif args.command == "materialize-s3":
        store = S3ReleaseStore.from_boto3(
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            prefix=args.prefix,
        )
        result = store.materialize(
            args.destination,
            archive_id=args.archive_id,
            release_id=args.release_id,
            channel=args.channel,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
        payload = dataclasses.asdict(result)
        payload["destination"] = str(payload["destination"])
    else:
        receipt = create_staging_receipt(
            args.materialized_root,
            source_revision=args.source_revision,
            source_sha256=args.source_sha256,
            runtime_lock_sha256=args.runtime_lock_sha256,
            python_version=args.python_version,
            channel=args.channel,
            materialized_path=args.materialized_path,
            expected_archive_id=args.expected_archive_id,
            expected_release_id=args.expected_release_id,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
        private_key = os.environ.get("MENDO_STAGING_RECEIPT_PRIVATE_KEY")
        key_id = os.environ.get("MENDO_STAGING_RECEIPT_KEY_ID")
        if not private_key or not key_id:
            raise InvalidEventError(
                "MENDO_STAGING_RECEIPT_PRIVATE_KEY and "
                "MENDO_STAGING_RECEIPT_KEY_ID are required"
            )
        signed = sign_staging_receipt(
            receipt,
            private_key=private_key,
            key_id=key_id,
        )
        print(serialize_model(signed).decode("utf-8"), end="")
        return
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
