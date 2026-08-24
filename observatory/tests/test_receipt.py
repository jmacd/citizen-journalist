from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mendo_observatory import (
    ArchiveStore,
    ReleaseBuilder,
    create_staging_receipt,
)
from mendo_observatory.errors import IntegrityError, InvalidEventError
from mendo_observatory import release_cli

def staging_metadata() -> dict[str, str]:
    return {
        "source_revision": "a" * 40,
        "source_sha256": "b" * 64,
        "runtime_lock_sha256": "c" * 64,
        "python_version": "3.11.2",
    }


def materialize_release(tmp_path: Path) -> tuple[Path, object]:
    archive_root = tmp_path / "archive"
    source = tmp_path / "record.pdf"
    source.write_bytes(b"receipt fixture")
    archive = ArchiveStore(archive_root)
    archive.initialize(birthplace="test")
    archive.ingest_file(
        source,
        record_id="record-1",
        record_title="Record One",
        collections=["case-1"],
    )
    release = ReleaseBuilder(archive_root).create(channel="staging")
    destination = tmp_path / "materialized"
    ReleaseBuilder(archive_root).materialize(destination, channel="staging")
    return destination, release


def test_creates_receipt_for_fully_verified_materialization(
    tmp_path: Path,
) -> None:
    destination, release = materialize_release(tmp_path)

    receipt = create_staging_receipt(
        destination,
        **staging_metadata(),
        channel="staging",
        materialized_path="/home/jmacd/observatory/releases/test",
        expected_archive_id=release.release.archive_id,
        expected_release_id=release.release.release_id,
        expected_manifest_sha256=release.manifest_sha256,
    )

    assert receipt.archive_id == release.release.archive_id
    assert receipt.release_id == release.release.release_id
    assert receipt.manifest_sha256 == release.manifest_sha256
    assert receipt.verified_file_count == len(release.release.entries) + 1
    assert receipt.materialized_path.startswith("/home/jmacd/")


def test_receipt_rejects_tampered_materialized_file(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)
    entry = release.release.entries[0]
    target = destination / entry.destination_path
    target.chmod(0o640)
    target.write_bytes(b"tampered")

    with pytest.raises(IntegrityError, match="receipt verification"):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_unmanifested_file(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)
    (destination / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    with pytest.raises(IntegrityError, match="file set differs"):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_unmanifested_directory(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)
    (destination / "unexpected").mkdir()

    with pytest.raises(IntegrityError, match="extra_directories"):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_missing_manifested_file(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)
    entry = release.release.entries[0]
    (destination / entry.destination_path).unlink()

    with pytest.raises(IntegrityError, match="missing="):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_unexpected_channel_result(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)

    with pytest.raises(IntegrityError, match="does not match the channel result"):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id="00000000-0000-4000-8000-000000000000",
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_symbolic_link(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)
    entry = release.release.entries[0]
    target = destination / entry.destination_path
    replacement = tmp_path / "replacement"
    replacement.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(replacement)

    with pytest.raises(IntegrityError, match="must not be a symlink"):
        create_staging_receipt(
            destination,
            **staging_metadata(),
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_rejects_invalid_source_revision(tmp_path: Path) -> None:
    destination, release = materialize_release(tmp_path)

    with pytest.raises(InvalidEventError, match="invalid staging receipt input"):
        create_staging_receipt(
            destination,
            source_revision="main",
            source_sha256="b" * 64,
            runtime_lock_sha256="c" * 64,
            python_version="3.11.2",
            channel="staging",
            materialized_path="/home/jmacd/observatory/releases/test",
            expected_archive_id=release.release.archive_id,
            expected_release_id=release.release.release_id,
            expected_manifest_sha256=release.manifest_sha256,
        )


def test_receipt_cli_emits_validated_contract(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    destination, release = materialize_release(tmp_path)
    monkeypatch.setenv(
        "MENDO_STAGING_RECEIPT_PRIVATE_KEY",
        base64.b64encode(
            Ed25519PrivateKey.from_private_bytes(bytes(range(32))).private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode("ascii"),
    )
    monkeypatch.setenv("MENDO_STAGING_RECEIPT_KEY_ID", "test-v1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mendo-release",
            "receipt",
            "--materialized-root",
            str(destination),
            "--materialized-path",
            "/home/jmacd/observatory/releases/test",
            "--source-revision",
            "a" * 40,
            "--source-sha256",
            "b" * 64,
            "--runtime-lock-sha256",
            "c" * 64,
            "--python-version",
            "3.11.2",
            "--channel",
            "staging",
            "--expected-archive-id",
            release.release.archive_id,
            "--expected-release-id",
            release.release.release_id,
            "--expected-manifest-sha256",
            release.manifest_sha256,
        ],
    )

    release_cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "mendo-signed-staging-release-receipt/v1"
    assert payload["signature_algorithm"] == "ed25519"
    assert payload["receipt"]["release_id"] == release.release.release_id
