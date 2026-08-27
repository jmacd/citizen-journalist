from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from mendo_agents.models import EvidenceGap
from mendo_agents.research_dispatch import ResearchDirectiveStore
from mendo_agents.research_queue import ResearchQueue
from mendo_agents.workbench import (
    CandidateStore,
    WorkbenchStore,
    is_trusted_private_client,
)


def test_trusted_private_clients_exclude_public_addresses() -> None:
    assert is_trusted_private_client("127.0.0.1")
    assert is_trusted_private_client("192.168.80.25")
    assert is_trusted_private_client("10.20.30.40")
    assert not is_trusted_private_client("8.8.8.8")
    assert not is_trusted_private_client("not-an-address")


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

    registration = store.record_registration(
        "official-record",
        candidates[0]["sha256"],
        "official_record",
        "captures/cases/CASE-1/official-record.pdf",
    )
    assert registration["source_id"] == "official_record"
    registered_candidate = store.candidate_with_decision("official-record")
    assert registered_candidate["canonical_registration"]["source_id"] == (
        "official_record"
    )
    with sqlite3.connect(queue_path) as connection:
        status = connection.execute(
            "SELECT status FROM research_queue WHERE id = ?", (lead.id,)
        ).fetchone()[0]
    assert status == "registered"
    queue.enqueue(
        "CASE-1",
        "Is the same approval still operative?",
        (
            EvidenceGap(
                description="The approval should be checked again.",
                deciding_record="Final agency approval",
                likely_custodian="Public Agency",
            ),
        ),
        origin_run_id="follow-up-run",
    )
    progress = store.progress_summary()
    assert progress["queue_statuses"] == {"registered": 1}
    assert progress["decision_count"] == 1
    assert progress["registration_count"] == 1
    assert progress["latest_activity_at"] is not None
    assert progress["latest_question"]["question"] == (
        "Is the same approval still operative?"
    )
    assert progress["latest_question"]["new_gap_count"] == 0
    assert progress["latest_question"]["matched_gap_count"] == 1
    assert progress["latest_question"]["gap_statuses"] == {"registered": 1}
    assert progress["triage_automation"]["state"] == "not_configured"


def test_progress_keeps_prior_directive_out_of_deduplicated_question(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    queue = ResearchQueue(queue_path)
    gap = EvidenceGap(
        description="The approval is missing.",
        deciding_record="Final agency approval",
        likely_custodian="Public Agency",
    )
    lead = queue.enqueue(
        "CASE-1",
        "First question",
        (gap,),
        origin_run_id="question-1",
    )[0]
    ResearchDirectiveStore(queue_path).create(
        "CASE-1",
        "Find final approval",
        "Retrieve the final approval.",
        (lead.id,),
        ("agency.example.gov",),
    )
    queue.enqueue(
        "CASE-1",
        "Follow-up question",
        (gap,),
        origin_run_id="question-2",
    )

    progress = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    ).progress_summary()

    assert progress["latest_question"]["run_id"] == "question-2"
    assert progress["latest_question"]["matched_gap_count"] == 1
    assert progress["latest_question"]["directive_statuses"] == {}


def test_progress_records_question_with_no_gaps(tmp_path: Path) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path).enqueue(
        "CASE-1",
        "Question with a complete answer",
        (),
        origin_run_id="question-no-gaps",
    )

    progress = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    ).progress_summary()

    assert progress["latest_question"]["run_id"] == "question-no-gaps"
    assert progress["latest_question"]["gap_count"] == 0
    assert progress["latest_question"]["gap_statuses"] == {}


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


def test_workbench_exposes_and_approves_bounded_research_directive(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    queue = ResearchQueue(queue_path)
    lead = queue.enqueue(
        "CASE-1",
        "Which permit is operative?",
        (
            EvidenceGap(
                description="The operative permit is missing.",
                deciding_record="Current permit",
                likely_custodian="State regulator",
            ),
        ),
    )[0]
    directive_store = ResearchDirectiveStore(queue_path)
    directive = directive_store.create(
        case_id="CASE-1",
        title="Locate the current permit",
        search_brief="Find the current official permit PDF.",
        lead_ids=[lead.id],
        allowed_hosts=["waterboards.ca.gov"],
    )
    store = WorkbenchStore(queue_path, CandidateStore(tmp_path / "staging"))

    activity = store.research_activity()
    assert activity[0]["id"] == directive.id
    assert activity[0]["status"] == "pending_approval"
    assert activity[0]["latest_run"] is None

    approved = store.approve_research_directive(directive.id, "cio")
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "cio"
    with sqlite3.connect(queue_path) as connection:
        status = connection.execute(
            "SELECT status FROM research_queue WHERE id = ?", (lead.id,)
        ).fetchone()[0]
    assert status == "approved_search"


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
    assert "What should I do now?" in html
    assert "This audit history does not require action" in html
    assert "Agent-produced evidence gaps" in html
    assert "Search directives and outcomes" in html
    assert "not questions awaiting your response" in html
    assert '<details class="research-drawer">' in html
    assert "innerHTML" not in javascript
    assert "canonical_registration_performed" in javascript
    assert "window.confirm" in javascript
    assert "Review decision complete" in javascript
    assert "Review next pending candidate" in javascript
    assert "function updateActionCenter()" in javascript
    assert "function renderProgressSummary()" in javascript
    assert "/api/workbench/progress" in javascript
    assert "No triage run is recorded yet" in javascript
    assert "Counts report persisted outcomes" in html
    assert "What is the system doing?" in html
    assert "Acquisition Engineer diagnosis" in javascript
    assert "No automatic triage worker is configured" in javascript
    assert "No action needed — research is running" in javascript
    assert "Workbench complete — return to chat" in javascript
    assert "function sortCandidates(items)" in javascript
    assert javascript.count("candidates = sortCandidates(") == 2
    assert "OpenStreetMap basemap" in javascript
    assert "Promise.allSettled(tileJobs)" in javascript
    assert "Approve and start Foundry search" in javascript
    assert "Start Foundry search" in javascript
    assert "/dispatch" in javascript
    assert "not a water-service area" in javascript
    assert "--host ${MENDO_WORKBENCH_HOST} --port 4180" in unit
    assert "${MENDO_WORKBENCH_EXTRA_ARGS}" in unit
    assert "EnvironmentFile=/home/jmacd/observatory/env/workbench.env" in unit
    assert "basic_auth" in caddy
    assert "X-Mendo-Workbench-Auth" in caddy
