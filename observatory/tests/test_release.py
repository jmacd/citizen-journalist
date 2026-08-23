from __future__ import annotations

import json
import stat
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from mendo_observatory import ArchiveStore, ReleaseBuilder
from mendo_observatory.errors import IntegrityError, InvalidEventError
from mendo_observatory.storage import hash_file


def seed_release_archive(root: Path) -> None:
    source = root.parent / "record.pdf"
    source.write_bytes(b"release fixture")
    store = ArchiveStore(root)
    store.initialize(birthplace="test")
    store.ingest_file(
        source,
        record_id="record-1",
        record_title="Record One",
        collections=["case-1"],
    )


def test_release_freezes_catalogs_and_advances_channel(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)

    result = ReleaseBuilder(archive_root).create(channel="private")

    assert result.manifest_path.is_file()
    assert result.channel_path == archive_root / "channels" / "private.json"
    channel = json.loads(result.channel_path.read_text())
    assert channel["release_id"] == result.release.release_id
    assert channel["manifest_sha256"] == result.manifest_sha256
    assert result.release.object_count == 1
    assert stat.S_IMODE(result.manifest_path.stat().st_mode) == 0o440
    assert all(
        stat.S_IMODE(
            (archive_root / entry.source_path).stat().st_mode
        )
        == 0o440
        for entry in result.release.entries
        if entry.source_path.startswith(f"releases/{result.release.release_id}/catalog/")
    )
    assert {entry.destination_path for entry in result.release.entries} >= {
        "archive.json",
        "catalog/records.parquet",
    }


def test_materializes_verified_release_into_clean_directory(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)
    release = ReleaseBuilder(archive_root).create(channel="public")
    destination = tmp_path / "materialized"

    result = ReleaseBuilder(archive_root).materialize(
        destination,
        channel="public",
    )

    assert result.release_id == release.release.release_id
    assert (destination / "release.json").is_file()
    assert (destination / "catalog" / "records.parquet").is_file()
    object_entry = next(
        entry
        for entry in release.release.entries
        if entry.destination_path.startswith("objects/")
    )
    materialized_object = destination / object_entry.destination_path
    assert hash_file(materialized_object) == (object_entry.sha256, object_entry.bytes)


def test_materialization_refuses_existing_destination(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)
    release = ReleaseBuilder(archive_root).create()
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(InvalidEventError, match="already exists"):
        ReleaseBuilder(archive_root).materialize(
            destination,
            release_id=release.release.release_id,
        )


def test_tampered_frozen_catalog_blocks_materialization(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)
    release = ReleaseBuilder(archive_root).create(channel="public")
    frozen_catalog = (
        archive_root
        / "releases"
        / release.release.release_id
        / "catalog"
        / "records.parquet"
    )
    frozen_catalog.chmod(0o640)
    frozen_catalog.write_bytes(b"tampered")
    destination = tmp_path / "materialized"

    with pytest.raises(IntegrityError, match="failed verification"):
        ReleaseBuilder(archive_root).materialize(destination, channel="public")

    assert not destination.exists()


def test_release_remains_self_consistent_after_live_corpus_changes(
    tmp_path: Path,
) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)
    first_release = ReleaseBuilder(archive_root).create()

    second_source = tmp_path / "second.pdf"
    second_source.write_bytes(b"second record")
    ArchiveStore(archive_root).ingest_file(
        second_source,
        record_id="record-2",
        record_title="Record Two",
        collections=["case-1"],
    )
    ReleaseBuilder(archive_root).create()

    destination = tmp_path / "first-release"
    ReleaseBuilder(archive_root).materialize(
        destination,
        release_id=first_release.release.release_id,
    )
    frozen_records = pq.read_table(
        destination / "catalog" / "records.parquet"
    ).to_pylist()

    assert [row["record_id"] for row in frozen_records] == ["record-1"]
    assert first_release.release.object_count == 1


def test_invalid_channel_creates_no_release(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_release_archive(archive_root)

    with pytest.raises(InvalidEventError, match="invalid release channel"):
        ReleaseBuilder(archive_root).create(channel="../public")

    assert not (archive_root / "releases").exists()
