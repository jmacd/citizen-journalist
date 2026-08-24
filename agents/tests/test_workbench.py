from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from mendo_agents.models import EvidenceGap
from mendo_agents.research_queue import ResearchQueue
from mendo_agents.workbench import CandidateStore, WorkbenchStore


def write_bundle(root: Path, lead_id: str) -> None:
    bundle_root = root / "run-1"
    bundle_root.mkdir(parents=True)
    evidence = bundle_root / "record.pdf"
    evidence.write_bytes(b"%PDF-1.7\nreview fixture\n%%EOF\n")
    preview = bundle_root / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    payload = {
        "schema_version": 1,
        "candidates": [
            {
                "id": "official-record",
                "title": "Official Record",
                "publisher": "Public Agency",
                "document_date": "2026-08-23",
                "source_url": "https://example.gov/record.pdf",
                "retrieved_at": "2026-08-24T03:00:00Z",
                "status": "staged",
                "version": "approved",
                "signature_status": "signed",
                "mime_type": "application/pdf",
                "bytes": evidence.stat().st_size,
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                "file_path": evidence.name,
                "preview_path": preview.name,
                "preview_bytes": preview.stat().st_size,
                "preview_sha256": hashlib.sha256(
                    preview.read_bytes()
                ).hexdigest(),
                "establishes": ["The agency approved the action."],
                "does_not_establish": ["A different agency's authority."],
                "related_lead_ids": [lead_id],
                "proposed_manifest": {
                    "id": "official_record",
                    "status": "captured",
                },
            }
        ],
    }
    (bundle_root / "review-bundle.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_workbench_lists_validated_candidate_and_records_approval(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    queue = ResearchQueue(queue_path)
    lead = queue.enqueue(
        "CASE-1",
        "What is operative?",
        (
            EvidenceGap(
                description="The approval is missing.",
                deciding_record="Final agency approval",
                likely_custodian="Public Agency",
            ),
        ),
    )[0]
    staging = tmp_path / "research-staging"
    write_bundle(staging, lead.id)
    store = WorkbenchStore(queue_path, CandidateStore(staging))

    candidates = store.candidates_with_decisions()
    assert candidates[0]["id"] == "official-record"
    assert candidates[0]["latest_decision"] is None
    assert candidates[0]["file_url"].endswith("/official-record/file")

    decision = store.decide(
        "official-record",
        candidates[0]["sha256"],
        "approve_registration",
        "Identity and provenance reviewed.",
        "cio",
    )

    assert decision["canonical_registration_performed"] is False
    assert decision["action"] == "approve_registration"
    assert store.candidate_with_decision("official-record")["latest_decision"][
        "note"
    ] == "Identity and provenance reviewed."
    with sqlite3.connect(queue_path) as connection:
        status = connection.execute(
            "SELECT status FROM research_queue WHERE id = ?", (lead.id,)
        ).fetchone()[0]
    assert status == "registration_approved"


def test_workbench_rejects_candidate_hash_mismatch(tmp_path: Path) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "lead-1")
    bundle_path = staging / "run-1" / "review-bundle.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["candidates"][0]["sha256"] = "0" * 64
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")

    store = CandidateStore(staging)
    assert store.list_candidates() == []
    assert "SHA-256 mismatch" in store.validation_errors[0]["error"]


def test_workbench_rejects_file_outside_staging_root(tmp_path: Path) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "lead-1")
    bundle_path = staging / "run-1" / "review-bundle.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.7\noutside\n")
    payload["candidates"][0]["file_path"] = "../../outside.pdf"
    payload["candidates"][0]["bytes"] = outside.stat().st_size
    payload["candidates"][0]["sha256"] = hashlib.sha256(
        outside.read_bytes()
    ).hexdigest()
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")

    store = CandidateStore(staging)
    assert store.list_candidates() == []
    assert "escapes staging root" in store.validation_errors[0]["error"]


def test_workbench_decision_survives_missing_related_lead(tmp_path: Path) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path)
    staging = tmp_path / "research-staging"
    write_bundle(staging, "missing-lead")
    store = WorkbenchStore(queue_path, CandidateStore(staging))

    decision = store.decide(
        "official-record",
        store.candidates.get_candidate("official-record")["sha256"],
        "continue_research",
        "Search received-copy agencies.",
        "cio",
    )

    assert decision["unmatched_lead_ids"] == ["missing-lead"]
    assert store.candidate_with_decision("official-record")["latest_decision"][
        "action"
    ] == "continue_research"


def test_workbench_rejects_decision_for_different_candidate_digest(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path)
    staging = tmp_path / "research-staging"
    write_bundle(staging, "missing-lead")
    store = WorkbenchStore(queue_path, CandidateStore(staging))

    try:
        store.decide(
            "official-record",
            "0" * 64,
            "approve_registration",
            "",
            "cio",
        )
    except RuntimeError as error:
        assert "changed after review" in str(error)
    else:
        raise AssertionError("Decision accepted a different candidate digest")


def test_workbench_requires_explicit_local_auth_bypass(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.pop("MENDO_WORKBENCH_PROXY_TOKEN", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mendo_agents.workbench",
            "--repo-root",
            str(repo_root),
            "--port",
            "0",
        ],
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "MENDO_WORKBENCH_PROXY_TOKEN is required" in result.stderr


def test_workbench_ui_and_watershop_service_preserve_approval_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    html = (repo_root / "web" / "workbench.html").read_text(encoding="utf-8")
    javascript = (repo_root / "web" / "workbench.js").read_text(encoding="utf-8")
    unit = (
        repo_root
        / "deploy"
        / "watershop"
        / "systemd"
        / "mendo-workbench.service"
    ).read_text(encoding="utf-8")
    caddy = (
        repo_root / "deploy" / "watershop" / "Caddyfile.workbench.example"
    ).read_text(encoding="utf-8")

    assert "canonical registration is a separate, deterministic step" in html
    assert "innerHTML" not in javascript
    assert "canonical_registration_performed" in javascript
    assert "window.confirm" in javascript
    assert "--host 127.0.0.1 --port 4180" in unit
    assert "EnvironmentFile=/home/jmacd/observatory/env/workbench.env" in unit
    assert "basic_auth" in caddy
    assert "X-Mendo-Workbench-Auth" in caddy
