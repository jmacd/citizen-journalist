from __future__ import annotations

import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from mendo_observatory import ArchiveStore, CorpusBuilder
from mendo_observatory.errors import IntegrityError, InvalidEventError


def seed_archive(root: Path) -> tuple[ArchiveStore, Path]:
    source = root.parent / "ordinance.pdf"
    source.write_bytes(b"certified ordinance")
    store = ArchiveStore(root)
    store.initialize(birthplace="test")
    result = store.ingest_file(
        source,
        record_id="mendocino-ordinance-3857",
        record_title="Mendocino County Ordinance 3857",
        collections=["mendocino-coastal-lcp", "ordinances"],
        source_url="https://example.gov/3857.pdf",
        custodian="Mendocino County",
    )
    return store, result.object_path


def test_builds_six_global_parquet_catalogs(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_archive(archive_root)

    result = CorpusBuilder(archive_root).build_catalogs()

    assert result.event_count == 1
    assert result.record_count == 1
    assert result.object_count == 1
    assert set(result.catalog_paths) == {
        "records",
        "objects",
        "renditions",
        "provenance-events",
        "relationships",
        "collection-memberships",
    }
    records = pq.read_table(result.catalog_paths["records"]).to_pylist()
    memberships = pq.read_table(
        result.catalog_paths["collection-memberships"]
    ).to_pylist()
    assert records[0]["record_id"] == "mendocino-ordinance-3857"
    assert {row["collection_id"] for row in memberships} == {
        "mendocino-coastal-lcp",
        "ordinances",
    }


def test_catalogs_rebuild_after_deletion(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_archive(archive_root)
    builder = CorpusBuilder(archive_root)
    first = builder.build_catalogs()
    first_bytes = {
        name: path.read_bytes() for name, path in first.catalog_paths.items()
    }

    for path in first.catalog_paths.values():
        path.unlink()
    second = builder.build_catalogs()

    assert {
        name: path.read_bytes() for name, path in second.catalog_paths.items()
    } == first_bytes


def test_verification_fails_loudly_on_corruption(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    _, object_path = seed_archive(archive_root)
    object_path.write_bytes(b"corrupted")

    with pytest.raises(IntegrityError, match="failed verification"):
        CorpusBuilder(archive_root).verify()


def test_missing_archive_root_does_not_create_empty_catalogs(tmp_path: Path) -> None:
    archive_root = tmp_path / "unmounted"

    with pytest.raises(InvalidEventError, match="not initialized"):
        CorpusBuilder(archive_root).build_catalogs()

    assert not archive_root.exists()


def test_empty_archive_requires_explicit_permission(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    ArchiveStore(archive_root).initialize(birthplace="test")

    with pytest.raises(InvalidEventError, match="no finalized events"):
        CorpusBuilder(archive_root).build_catalogs()

    result = CorpusBuilder(archive_root).build_catalogs(allow_empty=True)
    assert result.event_count == 0


def test_metadata_differences_do_not_poison_replay(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    first = tmp_path / "document.pdf"
    second = tmp_path / "document"
    first.write_bytes(b"same bytes")
    second.write_bytes(b"same bytes")
    store = ArchiveStore(archive_root)
    store.initialize(birthplace="test")
    store.ingest_file(
        first,
        record_id="shared-record",
        record_title="First observed title",
        collections=["one"],
    )
    store.ingest_file(
        second,
        record_id="shared-record",
        record_title="Corrected title",
        collections=["two"],
    )

    result = CorpusBuilder(archive_root).build_catalogs()
    record = pq.read_table(result.catalog_paths["records"]).to_pylist()[0]
    provenance = pq.read_table(
        result.catalog_paths["provenance-events"]
    ).to_pylist()

    assert record["title"] == "Corrected title"
    assert {row["media_type"] for row in provenance} == {
        "application/octet-stream",
        "application/pdf",
    }


def test_verification_reports_unreferenced_objects(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    seed_archive(archive_root)
    orphan_digest = "0" * 64
    orphan = archive_root / "objects" / "sha256" / "00" / orphan_digest
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"orphan")

    with pytest.raises(IntegrityError, match="unreferenced object"):
        CorpusBuilder(archive_root).verify()


def test_clean_workspace_rebuilds_from_identity_objects_and_events(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-archive"
    seed_archive(source_root)
    source_result = CorpusBuilder(source_root).build_catalogs()

    restored_root = tmp_path / "restored-archive"
    restored_root.mkdir()
    shutil.copy2(source_root / "archive.json", restored_root / "archive.json")
    shutil.copytree(source_root / "objects", restored_root / "objects")
    shutil.copytree(source_root / "events", restored_root / "events")
    restored_result = CorpusBuilder(restored_root).build_catalogs()

    for name in source_result.catalog_paths:
        source_rows = pq.read_table(source_result.catalog_paths[name]).to_pylist()
        restored_rows = pq.read_table(restored_result.catalog_paths[name]).to_pylist()
        assert restored_rows == source_rows
