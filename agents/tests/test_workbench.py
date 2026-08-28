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
from mendo_agents.research_triage import ResearchTriageStore
from mendo_agents.workbench import (
    CandidateStore,
    WorkbenchError,
    WorkbenchStore,
    is_trusted_private_client,
)


def test_trusted_private_clients_exclude_public_addresses() -> None:
    assert is_trusted_private_client("127.0.0.1")
    assert is_trusted_private_client("192.168.80.25")
    assert is_trusted_private_client("10.20.30.40")
    assert not is_trusted_private_client("8.8.8.8")
    assert not is_trusted_private_client("not-an-address")


def test_consultations_are_persisted_and_validated(tmp_path: Path) -> None:
    store = WorkbenchStore(
        tmp_path / "queue.sqlite",
        CandidateStore(tmp_path / "staging"),
    )
    created = store.create_consultation(
        "UM_2025-0004",
        "theorem_proposal",
        "  Compare recurring authority gaps. ",
        "cio",
    )

    assert created["status"] == "requested"
    assert created["brief"] == "Compare recurring authority gaps."
    assert store.consultations() == [created]

    try:
        store.create_consultation("UM_2025-0004", "unknown", "brief", "cio")
    except WorkbenchError as error:
        assert str(error) == "Unknown consultation type"
    else:
        raise AssertionError("invalid consultation type was accepted")


def write_bundle(root: Path, lead_id: str, run_id: str = "run-1") -> None:
    bundle_root = root / run_id
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


def test_workbench_merges_exact_cross_bundle_candidate_duplicates(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "lead-1", "run-1")
    write_bundle(staging, "lead-2", "run-2")
    second_bundle = staging / "run-2" / "review-bundle.json"
    payload = json.loads(second_bundle.read_text(encoding="utf-8"))
    payload["candidates"][0]["title"] = "Found by a second workflow"
    payload["candidates"][0]["version"] = "operative signed copy"
    payload["candidates"][0]["signature_status"] = "executed"
    payload["candidates"][0]["proposed_manifest"]["id"] = (
        "resolution_2026_333"
    )
    payload["candidates"][0]["source_url"] = (
        "https://EXAMPLE.GOV:443/record.pdf#download"
    )
    second_bundle.write_text(json.dumps(payload), encoding="utf-8")

    store = CandidateStore(staging)
    candidates = store.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["related_lead_ids"] == ["lead-1", "lead-2"]
    assert candidates[0]["duplicate_occurrence_count"] == 2
    assert [item["title"] for item in candidates[0]["occurrences"]] == [
        "Official Record",
        "Found by a second workflow",
    ]
    assert store.validation_errors == []


def test_workbench_rejects_conflicting_cross_bundle_candidate_duplicates(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "lead-1", "run-1")
    write_bundle(staging, "lead-2", "run-2")
    second_bundle = staging / "run-2" / "review-bundle.json"
    payload = json.loads(second_bundle.read_text(encoding="utf-8"))
    payload["candidates"][0]["source_url"] = (
        "https://example.gov/different-record.pdf"
    )
    second_bundle.write_text(json.dumps(payload), encoding="utf-8")

    store = CandidateStore(staging)
    candidates = store.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["related_lead_ids"] == ["lead-1"]
    assert "conflicting duplicate candidate ID" in (
        store.validation_errors[0]["error"]
    )
    assert "run-1/review-bundle.json" in store.validation_errors[0]["error"]
    assert "run-2/review-bundle.json" in store.validation_errors[0]["error"]


def test_workbench_rejects_duplicate_ids_within_one_bundle(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "lead-1")
    bundle = staging / "run-1" / "review-bundle.json"
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    payload["candidates"].append(dict(payload["candidates"][0]))
    bundle.write_text(json.dumps(payload), encoding="utf-8")

    store = CandidateStore(staging)

    assert store.list_candidates() == []
    assert "duplicate candidate ID within bundle" in (
        store.validation_errors[0]["error"]
    )


def test_invalid_bundle_does_not_reserve_candidate_id(tmp_path: Path) -> None:
    staging = tmp_path / "research-staging"
    write_bundle(staging, "invalid-lead", "a-invalid")
    invalid_bundle = staging / "a-invalid" / "review-bundle.json"
    payload = json.loads(invalid_bundle.read_text(encoding="utf-8"))
    payload["candidates"].append(dict(payload["candidates"][0]))
    invalid_bundle.write_text(json.dumps(payload), encoding="utf-8")
    write_bundle(staging, "valid-lead", "b-valid")

    store = CandidateStore(staging)
    candidates = store.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["related_lead_ids"] == ["valid-lead"]
    assert len(store.validation_errors) == 1


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


def test_question_provenance_graph_preserves_claim_gap_rationale(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    queue = ResearchQueue(queue_path)
    snapshot = {
        "schema_version": 1,
        "disposition": "answer_ready",
        "analysis": {
            "short_answer": "The order authorizes the general program.",
            "answer_claim_indices": [0],
            "claims": [
                {
                    "text": "The order authorizes the general program.",
                    "confidence": "supported_interpretation",
                    "does_not_establish": "Approval of this project site.",
                    "citations": [
                        {
                            "document_id": "general-order",
                            "title": "General Order",
                            "publisher": "Public Agency",
                            "url": "https://example.gov/order.pdf",
                            "page": 4,
                            "section": None,
                            "timestamp": None,
                            "field": None,
                            "invalid": False,
                        },
                        {
                            "document_id": "general-order",
                            "title": "General Order",
                            "publisher": "Public Agency",
                            "url": "https://example.gov/order.pdf",
                            "page": 12,
                            "section": None,
                            "timestamp": None,
                            "field": None,
                            "invalid": False,
                        },
                    ],
                }
            ],
        },
        "review": {"accepted": True, "findings": []},
    }
    gap = EvidenceGap(
        description="Project approval is unresolved.",
        deciding_record="Project-specific approval",
        likely_custodian="Public Agency",
        rationale=(
            "The general order does not identify this project site."
        ),
        related_claim_indices=(0,),
    )
    lead = queue.enqueue(
        "CASE-1",
        "Was this project approved?",
        (gap,),
        origin_run_id="question-provenance",
        provenance_snapshot=snapshot,
    )[0]
    directive = ResearchDirectiveStore(queue_path).create(
        "CASE-1",
        "Find project approval",
        "Retrieve the project-specific approval.",
        (lead.id,),
        ("example.gov",),
        question_run_id="question-provenance",
    )
    store = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    )

    questions = store.provenance_questions()
    graph = store.provenance_graph("question-provenance")
    context = store.directive_context(directive.id)

    assert questions[0]["analysis_available"] is True
    assert questions[0]["claim_count"] == 1
    assert {node["kind"] for node in graph["nodes"]} == {
        "question",
        "claim",
        "source",
        "gap",
        "directive",
    }
    relationship = next(
        edge
        for edge in graph["edges"]
        if edge["kind"] == "requires_record"
    )
    assert relationship["source"] == "claim:question-provenance:0"
    assert relationship["target"] == f"gap:{lead.id}"
    assert relationship["rationale"] == gap.rationale
    assert len(
        [
            edge
            for edge in graph["edges"]
            if edge["kind"] == "supported_by"
        ]
    ) == 2
    assert any(
        edge["target"] == f"directive:{directive.id}"
        and edge["kind"] == "investigated_by"
        and edge["attribution"] == "recorded"
        for edge in graph["edges"]
    )
    assert context["relevance_basis"] == "explicit_claim_limit"
    assert context["questions"][0]["question"] == "Was this project approved?"
    assert context["questions"][0]["gaps"][0]["related_claims"][0]["text"] == (
        "The order authorizes the general program."
    )
    assert "provisional" in context["caveat"]


def test_legacy_question_graph_does_not_invent_semantic_nodes(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path).enqueue(
        "CASE-1",
        "Legacy question",
        (),
        origin_run_id="legacy-question",
    )
    graph = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    ).provenance_graph("legacy-question")

    assert graph["semantic_analysis_available"] is False
    assert [node["kind"] for node in graph["nodes"]] == ["question"]
    assert graph["edges"] == []


def test_question_graph_reads_legacy_triage_schema(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path).enqueue(
        "CASE-1",
        "Legacy triage question",
        (),
        origin_run_id="legacy-triage-question",
    )
    with sqlite3.connect(queue_path) as connection:
        connection.execute(
            """
            CREATE TABLE research_triage_runs (
              id INTEGER PRIMARY KEY,
              question_run_id TEXT NOT NULL,
              status TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT,
              started_at TEXT NOT NULL,
              completed_at TEXT,
              output_json TEXT,
              error_type TEXT,
              error TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO research_triage_runs
              (id, question_run_id, status, provider, started_at)
            VALUES (1, 'legacy-triage-question', 'completed', 'foundry',
                    '2026-08-27T01:00:00+00:00')
            """
        )

    graph = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    ).provenance_graph("legacy-triage-question")

    assert any(node["kind"] == "triage" for node in graph["nodes"])
    assert not any(edge["kind"] == "prepared" for edge in graph["edges"])


def test_progress_reports_healthy_foundry_triage_loop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_path = tmp_path / "research-queue.sqlite"
    ResearchQueue(queue_path).enqueue(
        "CASE-1",
        "Question awaiting autonomous triage",
        (
            EvidenceGap(
                description="The policy is missing.",
                deciding_record="Final policy",
                likely_custodian="Public Agency",
            ),
        ),
        origin_run_id="question-foundry-loop",
    )
    ResearchTriageStore(queue_path).heartbeat("idle")
    monkeypatch.setenv("MENDO_TRIAGE_AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("MENDO_TRIAGE_POLL_SECONDS", "30")

    progress = WorkbenchStore(
        queue_path,
        CandidateStore(tmp_path / "staging"),
    ).progress_summary()

    assert progress["triage_automation"]["configured"] is True
    assert progress["triage_automation"]["healthy"] is True
    assert progress["triage_automation"]["state"] == "idle"
    assert progress["triage_automation"]["copilot_required"] is False


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
    assert "Automation loop status" in html
    assert "Question evidence map" in html
    assert "not hidden model" in html
    assert "/api/workbench/provenance/questions" in javascript
    assert "function renderProvenanceGraph(graph)" in javascript
    assert javascript.count("loadProvenanceQuestions(),") == 2
    assert "Why might this be relevant?" in javascript
    assert "/context" in javascript
    assert "this question predates persisted claim text" in javascript
    assert "Acquisition Engineer diagnosis" in javascript
    assert "IN THE LOOP — Foundry research is running" in javascript
    assert "OUT OF THE LOOP — no agent is processing these gaps" in javascript
    assert "directiveActionsInFlight" in javascript
    assert "researchActivityLoadSequence" in javascript
    assert "postJSONWithTimeout" in javascript
    assert "watershop may still be processing" in javascript
    assert "compare the workflow ID" in html
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
