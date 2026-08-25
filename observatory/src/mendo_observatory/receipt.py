"""Verified staging receipts for immutable release promotion."""

from __future__ import annotations

import hashlib
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pydantic import ValidationError

from .contracts import (
    CorpusRelease,
    SignedStagingReleaseReceipt,
    StagingReleaseReceipt,
    utc_now,
)
from .errors import IntegrityError, InvalidEventError
from .release import serialize_model
from .storage import hash_file


def create_staging_receipt(
    materialized_root: Path,
    *,
    source_revision: str,
    source_sha256: str,
    runtime_lock_sha256: str,
    python_version: str,
    channel: str,
    materialized_path: str,
    expected_archive_id: str,
    expected_release_id: str,
    expected_manifest_sha256: str,
) -> StagingReleaseReceipt:
    root = materialized_root.resolve()
    if not root.is_dir():
        raise InvalidEventError(
            f"materialized release directory is unavailable: {root}"
        )

    manifest_path = root / "release.json"
    if manifest_path.is_symlink():
        raise IntegrityError(
            f"materialized release manifest must not be a symlink: {manifest_path}"
        )
    try:
        manifest_payload = manifest_path.read_bytes()
        release = CorpusRelease.model_validate_json(manifest_payload)
    except (OSError, ValidationError, ValueError) as error:
        raise InvalidEventError(
            f"invalid materialized release manifest {manifest_path}: {error}"
        ) from error

    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    manifest_bytes = len(manifest_payload)
    if (
        release.archive_id != expected_archive_id
        or release.release_id != expected_release_id
        or manifest_sha256 != expected_manifest_sha256
    ):
        raise IntegrityError(
            "materialized release identity does not match the channel result"
        )

    expected_paths = {"release.json"}
    expected_directories: set[str] = set()
    for entry in release.entries:
        parent = Path(entry.destination_path).parent
        while parent != Path("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
        expected_paths.add(entry.destination_path)

    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    actual_directories = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir() and not path.is_symlink()
    }
    if actual_paths != expected_paths or actual_directories != expected_directories:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        missing_directories = sorted(expected_directories - actual_directories)
        extra_directories = sorted(actual_directories - expected_directories)
        raise IntegrityError(
            f"materialized release file set differs from manifest; "
            f"missing={missing}, extra={extra}, "
            f"missing_directories={missing_directories}, "
            f"extra_directories={extra_directories}"
        )

    verified_bytes = manifest_bytes
    for entry in release.entries:
        path = root / entry.destination_path
        if path.is_symlink():
            raise IntegrityError(
                f"materialized release file must not be a symlink: {path}"
            )
        actual_sha256, actual_bytes = hash_file(path)
        if actual_sha256 != entry.sha256 or actual_bytes != entry.bytes:
            raise IntegrityError(
                f"materialized release file failed receipt verification: {path}"
            )
        verified_bytes += actual_bytes

    symlinks = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_symlink()
    )
    if symlinks:
        raise IntegrityError(
            f"materialized release contains symbolic links: {symlinks}"
        )
    try:
        return StagingReleaseReceipt(
            source_revision=source_revision,
            source_sha256=source_sha256,
            runtime_lock_sha256=runtime_lock_sha256,
            python_version=python_version,
            archive_id=release.archive_id,
            release_id=release.release_id,
            channel=channel,
            manifest_sha256=manifest_sha256,
            verified_at=utc_now(),
            verified_file_count=len(expected_paths),
            verified_bytes=verified_bytes,
            materialized_path=materialized_path,
        )
    except ValidationError as error:
        raise InvalidEventError(f"invalid staging receipt input: {error}") from error


def sign_staging_receipt(
    receipt: StagingReleaseReceipt,
    *,
    private_key: str,
    key_id: str,
) -> SignedStagingReleaseReceipt:
    try:
        key_bytes = base64.b64decode(private_key, validate=True)
        signer = load_pem_private_key(key_bytes, password=None)
        if not isinstance(signer, Ed25519PrivateKey):
            raise ValueError("private key is not Ed25519")
    except (TypeError, ValueError) as error:
        raise InvalidEventError(
            "staging receipt private key must be a base64-encoded "
            "unencrypted Ed25519 PEM key"
        ) from error
    signature = base64.b64encode(
        signer.sign(staging_receipt_signature_payload(receipt, key_id=key_id))
    ).decode("ascii")
    try:
        return SignedStagingReleaseReceipt(
            key_id=key_id,
            receipt=receipt,
            signature=signature,
        )
    except ValidationError as error:
        raise InvalidEventError(f"invalid staging receipt signature: {error}") from error


def staging_receipt_signature_payload(
    receipt: StagingReleaseReceipt,
    *,
    key_id: str,
) -> bytes:
    return (
        json.dumps(
            {
                "key_id": key_id,
                "receipt": receipt.model_dump(mode="json", by_alias=True),
                "schema": "mendo-signed-staging-release-receipt/v1",
                "signature_algorithm": "ed25519",
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
