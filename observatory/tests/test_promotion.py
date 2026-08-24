from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mendo_observatory.contracts import StagingReleaseReceipt
from mendo_observatory.errors import IntegrityError, InvalidEventError
from mendo_observatory.promotion import (
    create_promotion_candidate,
    verify_image_index,
)
from mendo_observatory.receipt import sign_staging_receipt
from mendo_observatory.release import serialize_model

SOURCE_REVISION = "d" * 40


PRIVATE_KEY_BYTES = bytes(range(32))
TEST_SIGNER = Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY_BYTES)
PRIVATE_KEY = base64.b64encode(
    TEST_SIGNER.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
).decode("ascii")
PUBLIC_KEY = TEST_SIGNER.public_key().public_bytes(
    encoding=serialization.Encoding.OpenSSH,
    format=serialization.PublicFormat.OpenSSH,
).decode("ascii")


def write_receipt(path: Path) -> bytes:
    receipt = StagingReleaseReceipt(
        source_revision=SOURCE_REVISION,
        source_sha256="e" * 64,
        runtime_lock_sha256="f" * 64,
        python_version="3.11.2",
        archive_id="00000000-0000-4000-8000-000000000001",
        release_id="00000000-0000-4000-8000-000000000002",
        channel="staging",
        manifest_sha256="b" * 64,
        verified_at=datetime(2026, 8, 23, tzinfo=timezone.utc),
        verified_file_count=8,
        verified_bytes=1024,
        materialized_path="/home/jmacd/observatory/releases/release",
    )
    payload = serialize_model(
        sign_staging_receipt(
            receipt,
            private_key=PRIVATE_KEY,
            key_id="test-v1",
        )
    )
    path.write_bytes(payload)
    return payload


def write_index(path: Path, platforms: list[tuple[str, str]]) -> bytes:
    payload = json.dumps(
        {
            "schemaVersion": 2,
            "manifests": [
                {"platform": {"os": operating_system, "architecture": architecture}}
                for operating_system, architecture in platforms
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    path.write_bytes(payload)
    return payload


def test_verifies_both_required_image_platforms(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    payload = write_index(
        index,
        [
            ("linux", "amd64"),
            ("unknown", "unknown"),
            ("linux", "arm64"),
        ],
    )

    assert verify_image_index(
        index,
        expected_digest=hashlib.sha256(payload).hexdigest(),
    )[0] == ["linux/amd64", "linux/arm64"]


def test_rejects_image_index_missing_staging_platform(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    payload = write_index(index, [("linux", "amd64")])

    with pytest.raises(IntegrityError, match="linux/arm64"):
        verify_image_index(
            index,
            expected_digest=hashlib.sha256(payload).hexdigest(),
        )


def test_rejects_image_index_with_wrong_digest(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    write_index(index, [("linux", "amd64"), ("linux", "arm64")])

    with pytest.raises(IntegrityError, match="do not match"):
        verify_image_index(index, expected_digest="0" * 64)


def test_candidate_binds_exact_receipt_bytes(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_payload = write_index(
        index_path,
        [("linux", "amd64"), ("linux", "arm64")],
    )
    index_digest = hashlib.sha256(index_payload).hexdigest()
    image = f"ghcr.io/jmacd/mendo-codebook-observatory@sha256:{index_digest}"
    receipt_path = tmp_path / "receipt.json"
    receipt_payload = write_receipt(receipt_path)
    candidate_path = tmp_path / "candidate.json"

    candidate = create_promotion_candidate(
        receipt_path,
        index_path,
        candidate_path,
        image=image,
        image_revision=SOURCE_REVISION,
        public_key=PUBLIC_KEY,
        expected_image_repository="ghcr.io/jmacd/mendo-codebook-observatory",
        promoted_by="jmacd",
        source_repository="jmacd/mendo-codebook",
        source_revision=SOURCE_REVISION,
        source_ref="refs/heads/main",
        workflow_run_id="12345",
    )

    assert candidate.receipt_sha256 == hashlib.sha256(receipt_payload).hexdigest()
    assert candidate.image_index_sha256 == index_digest
    assert candidate.image == image
    assert candidate.image_platforms == ["linux/amd64", "linux/arm64"]
    assert candidate.disposition == "production_candidate"
    assert candidate_path.is_file()


def test_candidate_rejects_wrong_receipt_signature(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_payload = write_index(
        index_path,
        [("linux", "amd64"), ("linux", "arm64")],
    )
    image = (
        "ghcr.io/jmacd/mendo-codebook-observatory@sha256:"
        + hashlib.sha256(index_payload).hexdigest()
    )
    receipt_path = tmp_path / "receipt.json"
    write_receipt(receipt_path)

    with pytest.raises(IntegrityError, match="signature"):
        create_promotion_candidate(
            receipt_path,
            index_path,
            tmp_path / "candidate.json",
            image=image,
            image_revision=SOURCE_REVISION,
            public_key=Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
            .public_key()
            .public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH,
            )
            .decode("ascii"),
            expected_image_repository="ghcr.io/jmacd/mendo-codebook-observatory",
            promoted_by="jmacd",
            source_repository="jmacd/mendo-codebook",
            source_revision=SOURCE_REVISION,
            source_ref="refs/heads/main",
            workflow_run_id="12345",
        )


def test_candidate_rejects_tampered_receipt_key_id(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_payload = write_index(
        index_path,
        [("linux", "amd64"), ("linux", "arm64")],
    )
    image = (
        "ghcr.io/jmacd/mendo-codebook-observatory@sha256:"
        + hashlib.sha256(index_payload).hexdigest()
    )
    receipt_path = tmp_path / "receipt.json"
    write_receipt(receipt_path)
    envelope = json.loads(receipt_path.read_text(encoding="utf-8"))
    envelope["key_id"] = "forged-v2"
    receipt_path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(IntegrityError, match="signature"):
        create_promotion_candidate(
            receipt_path,
            index_path,
            tmp_path / "candidate.json",
            image=image,
            image_revision=SOURCE_REVISION,
            public_key=PUBLIC_KEY,
            expected_image_repository="ghcr.io/jmacd/mendo-codebook-observatory",
            promoted_by="jmacd",
            source_repository="jmacd/mendo-codebook",
            source_revision=SOURCE_REVISION,
            source_ref="refs/heads/main",
            workflow_run_id="12345",
        )


def test_candidate_rejects_other_image_repository(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_payload = write_index(
        index_path,
        [("linux", "amd64"), ("linux", "arm64")],
    )
    image = (
        "ghcr.io/other/project@sha256:"
        + hashlib.sha256(index_payload).hexdigest()
    )
    receipt_path = tmp_path / "receipt.json"
    write_receipt(receipt_path)

    with pytest.raises(InvalidEventError, match="must use"):
        create_promotion_candidate(
            receipt_path,
            index_path,
            tmp_path / "candidate.json",
            image=image,
            image_revision=SOURCE_REVISION,
            public_key=PUBLIC_KEY,
            expected_image_repository="ghcr.io/jmacd/mendo-codebook-observatory",
            promoted_by="jmacd",
            source_repository="jmacd/mendo-codebook",
            source_revision=SOURCE_REVISION,
            source_ref="refs/heads/main",
            workflow_run_id="12345",
        )


def test_candidate_rejects_image_from_different_revision(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_payload = write_index(
        index_path,
        [("linux", "amd64"), ("linux", "arm64")],
    )
    image = (
        "ghcr.io/jmacd/mendo-codebook-observatory@sha256:"
        + hashlib.sha256(index_payload).hexdigest()
    )
    receipt_path = tmp_path / "receipt.json"
    write_receipt(receipt_path)

    with pytest.raises(IntegrityError, match="revision"):
        create_promotion_candidate(
            receipt_path,
            index_path,
            tmp_path / "candidate.json",
            image=image,
            image_revision="0" * 40,
            public_key=PUBLIC_KEY,
            expected_image_repository="ghcr.io/jmacd/mendo-codebook-observatory",
            promoted_by="jmacd",
            source_repository="jmacd/mendo-codebook",
            source_revision=SOURCE_REVISION,
            source_ref="refs/heads/main",
            workflow_run_id="12345",
        )
