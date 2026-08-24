"""Validation and audit artifacts for immutable production promotion."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_ssh_public_key

from .contracts import (
    ProductionPromotionCandidate,
    SignedStagingReleaseReceipt,
    utc_now,
)
from .errors import IntegrityError, InvalidEventError
from .release import serialize_model
from .receipt import staging_receipt_signature_payload
from .storage import write_create_only

REQUIRED_PLATFORMS = {"linux/amd64", "linux/arm64"}


def load_staging_receipt(
    path: Path,
    *,
    public_key: str,
) -> tuple[SignedStagingReleaseReceipt, str]:
    try:
        payload = path.read_bytes()
        envelope = SignedStagingReleaseReceipt.model_validate_json(payload)
    except (OSError, ValidationError, ValueError) as error:
        raise InvalidEventError(f"invalid staging receipt {path}: {error}") from error
    try:
        verifier = load_ssh_public_key(public_key.encode("ascii"))
        if not isinstance(verifier, Ed25519PublicKey):
            raise ValueError("public key is not Ed25519")
        verifier.verify(
            base64.b64decode(envelope.signature, validate=True),
            staging_receipt_signature_payload(
                envelope.receipt,
                key_id=envelope.key_id,
            ),
        )
    except (InvalidSignature, TypeError, ValueError) as error:
        raise IntegrityError("staging receipt signature verification failed") from error
    return envelope, hashlib.sha256(payload).hexdigest()


def validate_image_reference(image: str, *, expected_repository: str) -> str:
    prefix = f"{expected_repository}@sha256:"
    digest = image.removeprefix(prefix)
    if not image.startswith(prefix) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise InvalidEventError(
            f"image must use {expected_repository} pinned by a SHA-256 digest"
        )
    return digest


def verify_image_index(path: Path, *, expected_digest: str) -> tuple[list[str], str]:
    try:
        raw = path.read_bytes()
        image_index_sha256 = hashlib.sha256(raw).hexdigest()
        if image_index_sha256 != expected_digest:
            raise IntegrityError(
                "OCI image index bytes do not match the receipt image digest"
            )
        payload = json.loads(raw)
        manifests = payload["manifests"]
        platforms = {
            f"{manifest['platform']['os']}/{manifest['platform']['architecture']}"
            for manifest in manifests
            if isinstance(manifest.get("platform"), dict)
            and manifest["platform"].get("os") == "linux"
        }
    except (AttributeError, OSError, KeyError, TypeError, ValueError) as error:
        raise InvalidEventError(f"invalid OCI image index {path}: {error}") from error

    missing = sorted(REQUIRED_PLATFORMS - platforms)
    if missing:
        raise IntegrityError(
            f"OCI image index lacks required promotion platforms: {missing}"
        )
    return sorted(REQUIRED_PLATFORMS), image_index_sha256


def create_promotion_candidate(
    receipt_path: Path,
    image_index_path: Path,
    output_path: Path,
    *,
    image: str,
    image_revision: str,
    public_key: str,
    expected_image_repository: str,
    promoted_by: str,
    source_repository: str,
    source_revision: str,
    source_ref: str,
    workflow_run_id: str,
) -> ProductionPromotionCandidate:
    receipt, receipt_sha256 = load_staging_receipt(
        receipt_path,
        public_key=public_key,
    )
    if source_revision != receipt.receipt.source_revision:
        raise IntegrityError(
            "promotion workflow revision does not match the staged source revision"
        )
    if image_revision != receipt.receipt.source_revision:
        raise IntegrityError(
            "production image revision does not match the staged source revision"
        )
    expected_image_digest = validate_image_reference(
        image,
        expected_repository=expected_image_repository,
    )
    image_platforms, image_index_sha256 = verify_image_index(
        image_index_path,
        expected_digest=expected_image_digest,
    )
    try:
        candidate = ProductionPromotionCandidate(
            receipt_sha256=receipt_sha256,
            receipt=receipt,
            image=image,
            image_index_sha256=image_index_sha256,
            image_platforms=image_platforms,
            promoted_at=utc_now(),
            promoted_by=promoted_by,
            source_repository=source_repository,
            source_revision=source_revision,
            source_ref=source_ref,
            workflow_run_id=workflow_run_id,
        )
    except ValidationError as error:
        raise InvalidEventError(f"invalid promotion candidate input: {error}") from error
    write_create_only(output_path, serialize_model(candidate), file_mode=0o440)
    return candidate
