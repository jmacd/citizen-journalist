from __future__ import annotations

import json
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mendo_observatory import ArchiveStore
from mendo_observatory.errors import ArchiveWriteError
from mendo_observatory.contracts import ObjectStoredEvent


def test_ingest_writes_content_addressed_object_and_event(tmp_path: Path) -> None:
    source = tmp_path / "resolution.pdf"
    source.write_bytes(b"%PDF fixture")
    archive_root = tmp_path / "archive"
    store = ArchiveStore(archive_root)
    identity = store.initialize(birthplace="test")

    result = store.ingest_file(
        source,
        record_id="county-pc-2024-0019",
        record_title="Resolution PC 2024-0019",
        collections=["county-resolutions", "UM_2025-0004"],
        source_url="https://example.gov/resolution.pdf",
        custodian="Mendocino County",
    )

    assert result.object_created is True
    assert result.object_path.read_bytes() == source.read_bytes()
    event = ObjectStoredEvent.model_validate_json(result.event_path.read_bytes())
    assert event.object.sha256 == result.event.object.sha256
    assert event.collections == ["UM_2025-0004", "county-resolutions"]
    assert stat.S_IMODE(result.object_path.stat().st_mode) == 0o640
    assert stat.S_IMODE(result.event_path.stat().st_mode) == 0o640
    assert json.loads(result.event_path.read_text())["schema"] == "mendo-corpus-event/v1"
    assert identity.archive_id
    assert json.loads((archive_root / "archive.json").read_text())["schema"] == "mendo-archive/v1"


def test_duplicate_bytes_reuse_object_but_preserve_acquisition_event(tmp_path: Path) -> None:
    source = tmp_path / "guideline.pdf"
    source.write_bytes(b"same bytes")
    store = ArchiveStore(tmp_path / "archive")
    store.initialize(birthplace="test")

    first = store.ingest_file(
        source,
        record_id="groundwater-guideline",
        record_title="Groundwater Guideline",
        collections=["coastal-groundwater"],
    )
    second = store.ingest_file(
        source,
        record_id="groundwater-guideline",
        record_title="Groundwater Guideline",
        collections=["UM_2025-0004"],
    )

    assert first.object_created is True
    assert second.object_created is False
    assert first.object_path == second.object_path
    assert first.event_path != second.event_path


def test_preserves_explicit_retrieval_time(tmp_path: Path) -> None:
    source = tmp_path / "historic.pdf"
    source.write_bytes(b"historic")
    retrieved_at = datetime(1993, 11, 9, 12, 0, tzinfo=timezone.utc)

    store = ArchiveStore(tmp_path / "archive")
    store.initialize(birthplace="test")
    result = store.ingest_file(
        source,
        record_id="ordinance-3857",
        record_title="Ordinance 3857",
        collections=["ordinances"],
        retrieved_at=retrieved_at,
    )

    assert result.event.source.retrieved_at == retrieved_at


def test_ingest_refuses_uninitialized_mountpoint(tmp_path: Path) -> None:
    source = tmp_path / "record.pdf"
    source.write_bytes(b"record")
    archive_root = tmp_path / "unmounted-archive"
    archive_root.mkdir()

    with pytest.raises(ArchiveWriteError, match="not initialized"):
        ArchiveStore(archive_root).ingest_file(
            source,
            record_id="record",
            record_title="Record",
            collections=["test"],
        )

    assert not (archive_root / "objects").exists()
