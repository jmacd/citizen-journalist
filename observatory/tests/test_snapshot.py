from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from mendo_observatory import ArchiveStore
from mendo_observatory.errors import ArchiveWriteError
from mendo_observatory.snapshot import CaptureSnapshotStore


def test_snapshot_restores_files_and_consistent_sqlite(
    tmp_path: Path,
) -> None:
    source = tmp_path / "workspace"
    captures = source / "captures"
    cases = source / "cases" / "CASE-1"
    captures.mkdir(parents=True)
    cases.mkdir(parents=True)
    (captures / "record.pdf").write_bytes(b"%PDF accepted record")
    database = captures / "research-queue.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE decisions (id INTEGER PRIMARY KEY, action TEXT)"
        )
        connection.execute(
            "INSERT INTO decisions (action) VALUES ('approve_registration')"
        )
    (cases / "manifest.yaml").write_text(
        "sources:\n  - id: accepted-record\n",
        encoding="utf-8",
    )

    archive_root = tmp_path / "archive"
    ArchiveStore(archive_root).initialize(birthplace="test")
    snapshots = CaptureSnapshotStore(archive_root)
    result = snapshots.create(
        source,
        source_revision="1" * 40,
        includes=["captures", "cases/CASE-1"],
        source_label="test-workstation",
        collection="CASE-1",
        snapshot_id="00000000-0000-4000-8000-000000000010",
    )

    assert result.file_event_count == 3
    assert result.snapshot.entries[0].path == "captures/record.pdf"
    manifest = json.loads(result.manifest_object_path.read_text())
    assert manifest["schema"] == "mendo-capture-snapshot/v1"

    destination = tmp_path / "restored"
    restored = snapshots.restore(result.snapshot.snapshot_id, destination)
    assert restored.restored_file_count == 3
    assert (destination / "captures/record.pdf").read_bytes() == (
        b"%PDF accepted record"
    )
    with sqlite3.connect(
        destination / "captures/research-queue.sqlite"
    ) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute(
            "SELECT action FROM decisions"
        ).fetchone()[0] == "approve_registration"
    assert (destination / "cases/CASE-1/manifest.yaml").read_text() == (
        "sources:\n  - id: accepted-record\n"
    )


def test_snapshot_restore_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "workspace"
    source.mkdir()
    (source / "record.txt").write_text("record", encoding="utf-8")
    archive_root = tmp_path / "archive"
    ArchiveStore(archive_root).initialize(birthplace="test")
    snapshots = CaptureSnapshotStore(archive_root)
    result = snapshots.create(
        source,
        source_revision="2" * 40,
        includes=["record.txt"],
        source_label="test",
        collection="test",
    )
    destination = tmp_path / "restored"
    destination.mkdir()

    with pytest.raises(ArchiveWriteError, match="already exists"):
        snapshots.restore(result.snapshot.snapshot_id, destination)
