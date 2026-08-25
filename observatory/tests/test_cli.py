from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_module(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def test_cli_initializes_ingests_builds_and_verifies(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    source = tmp_path / "record.txt"
    source.write_text("official record\n", encoding="utf-8")

    initialized = run_module(
        "mendo_observatory.archive_cli",
        "init",
        "--root",
        str(archive_root),
        "--birthplace",
        "test-station",
        "--archive-id",
        "00000000-0000-4000-8000-000000000001",
    )
    identity = json.loads(initialized.stdout)
    assert identity["schema"] == "mendo-archive/v1"
    assert identity["birthplace"] == "test-station"
    assert identity["archive_id"] == "00000000-0000-4000-8000-000000000001"

    ingested = run_module(
        "mendo_observatory.archive_cli",
        "ingest",
        str(source),
        "--root",
        str(archive_root),
        "--record-id",
        "official-record",
        "--title",
        "Official Record",
        "--collection",
        "case-1",
        "--retrieved-at",
        "2026-08-22T12:00:00+00:00",
    )
    ingest_result = json.loads(ingested.stdout)
    assert ingest_result["object_created"] is True

    built = run_module(
        "mendo_observatory.corpus_cli",
        "build",
        "--root",
        str(archive_root),
    )
    assert json.loads(built.stdout)["record_count"] == 1

    verified = run_module(
        "mendo_observatory.corpus_cli",
        "verify",
        "--root",
        str(archive_root),
    )
    assert json.loads(verified.stdout)["object_count"] == 1


def test_cli_invalid_metadata_creates_no_archive_object(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    source = tmp_path / "record.txt"
    source.write_text("official record\n", encoding="utf-8")
    run_module(
        "mendo_observatory.archive_cli",
        "init",
        "--root",
        str(archive_root),
        "--birthplace",
        "test-station",
    )

    failed = run_module(
        "mendo_observatory.archive_cli",
        "ingest",
        str(source),
        "--root",
        str(archive_root),
        "--record-id",
        "../unsafe",
        "--title",
        "Official Record",
        "--collection",
        "case-1",
        check=False,
    )

    assert failed.returncode != 0
    assert not list((archive_root / "objects" / "sha256").glob("*/*"))
    assert not list((archive_root / "events").glob("*/*.json"))
