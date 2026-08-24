"""CLI for validating staging receipts and producing promotion candidates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .errors import InvalidEventError
from .promotion import (
    create_promotion_candidate,
    load_staging_receipt,
    validate_image_reference,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-promote")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-receipt")
    validate.add_argument("--receipt", type=Path, required=True)
    validate.add_argument("--github-output", type=Path)

    image = subparsers.add_parser("validate-image")
    image.add_argument("--image", required=True)
    image.add_argument("--expected-image-repository", required=True)
    image.add_argument("--github-output", type=Path)

    candidate = subparsers.add_parser("create-candidate")
    candidate.add_argument("--receipt", type=Path, required=True)
    candidate.add_argument("--image-index", type=Path, required=True)
    candidate.add_argument("--output", type=Path, required=True)
    candidate.add_argument("--image", required=True)
    candidate.add_argument("--image-revision", required=True)
    candidate.add_argument("--expected-image-repository", required=True)
    candidate.add_argument("--promoted-by", required=True)
    candidate.add_argument("--source-repository", required=True)
    candidate.add_argument("--source-revision", required=True)
    candidate.add_argument("--source-ref", required=True)
    candidate.add_argument("--workflow-run-id", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "validate-receipt":
        public_key = require_public_key()
        envelope, receipt_sha256 = load_staging_receipt(
            args.receipt,
            public_key=public_key,
        )
        receipt = envelope.receipt
        payload = {
            "archive_id": receipt.archive_id,
            "manifest_sha256": receipt.manifest_sha256,
            "receipt_sha256": receipt_sha256,
            "release_id": receipt.release_id,
            "source_revision": receipt.source_revision,
        }
        if args.github_output is not None:
            with args.github_output.open("a", encoding="utf-8") as output:
                for key, value in sorted(payload.items()):
                    output.write(f"{key}={value}\n")
    elif args.command == "validate-image":
        digest = validate_image_reference(
            args.image,
            expected_repository=args.expected_image_repository,
        )
        payload = {"image": args.image, "image_digest": digest}
        if args.github_output is not None:
            with args.github_output.open("a", encoding="utf-8") as output:
                for key, value in sorted(payload.items()):
                    output.write(f"{key}={value}\n")
    else:
        public_key = require_public_key()
        candidate = create_promotion_candidate(
            args.receipt,
            args.image_index,
            args.output,
            image=args.image,
            image_revision=args.image_revision,
            public_key=public_key,
            expected_image_repository=args.expected_image_repository,
            promoted_by=args.promoted_by,
            source_repository=args.source_repository,
            source_revision=args.source_revision,
            source_ref=args.source_ref,
            workflow_run_id=args.workflow_run_id,
        )
        payload = {
            "image": candidate.image,
            "receipt_sha256": candidate.receipt_sha256,
            "release_id": candidate.receipt.receipt.release_id,
        }
    print(json.dumps(payload, sort_keys=True))


def require_public_key() -> str:
    public_key = os.environ.get("MENDO_STAGING_RECEIPT_PUBLIC_KEY")
    if not public_key:
        raise InvalidEventError("MENDO_STAGING_RECEIPT_PUBLIC_KEY is required")
    return public_key


if __name__ == "__main__":
    main()
