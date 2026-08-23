from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent_framework import FileCheckpointStorage

from mendo_agents.models import (
    ApprovalBundle,
    ApprovalDecision,
    CaseQuestion,
    DispositionKind,
    EvidenceLocator,
    MonitorObservation,
)
from mendo_agents.policy import load_society_policy
from mendo_agents.providers import ScriptedReasoner
from mendo_agents.repository import CorpusRepository
from mendo_agents.skills import load_skills
from mendo_agents.workflow import AnalystExecutor, build_evidence_workflow


REPO_ROOT = Path(__file__).resolve().parents[2]


def make_workflow(fixture_repo: Path, storage: FileCheckpointStorage):
    return build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        ScriptedReasoner(),
        storage,
    )


def test_analyst_output_supports_multiple_page_and_timestamp_locators() -> None:
    analysis = AnalystExecutor._parse(
        json.dumps(
            {
                "short_answer": "The records regulate separate layers.",
                "claims": [
                    {
                        "text": "The records regulate separate layers.",
                        "confidence": "supported_interpretation",
                        "locators": [
                            {"document_id": "letter", "page": 2},
                            {
                                "document_id": "hearing",
                                "timestamp": "01:10:03-01:10:49",
                            },
                        ],
                        "does_not_establish": "The records do not resolve every issue.",
                    }
                ],
                "answer_claim_indices": [0],
            }
        ),
        [],
    )

    assert analysis.claims[0].locators == (
        EvidenceLocator("letter", page=2),
        EvidenceLocator("hearing", timestamp="01:10:03-01:10:49"),
    )


async def test_workflow_requires_cio_approval_and_emits_cited_answer(
    fixture_repo: Path, tmp_path: Path
) -> None:
    storage = FileCheckpointStorage(tmp_path / "checkpoints")
    workflow = make_workflow(fixture_repo, storage)
    requests = {}

    async for event in workflow.run(
        CaseQuestion(
            case_id="TEST-CASE",
            question="Did the commission continue the hearing?",
        ),
        stream=True,
    ):
        if event.type == "request_info":
            assert isinstance(event.data, ApprovalBundle)
            requests[event.request_id] = ApprovalDecision(approved=True)

    assert requests
    output = None
    async for event in workflow.run(stream=True, responses=requests):
        if event.type == "output":
            output = event.data

    assert output is not None
    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.short_answer == (
        "The commission continued the hearing to September 3."
    )
    assert output.analysis.claims[0].locators[0].document_id == "minutes"
    assert output.analysis.claims[0].locators[0].page == 4


async def test_pending_approval_survives_checkpoint_rehydration(
    fixture_repo: Path, tmp_path: Path
) -> None:
    storage = FileCheckpointStorage(tmp_path / "checkpoints")
    workflow = make_workflow(fixture_repo, storage)

    async for _ in workflow.run(
        CaseQuestion(
            case_id="TEST-CASE",
            question="Did the commission continue the hearing?",
        ),
        stream=True,
    ):
        pass

    checkpoints = await storage.list_checkpoints(workflow_name=workflow.name)
    assert checkpoints
    latest = sorted(checkpoints, key=lambda value: value.timestamp)[-1]

    restarted_storage = FileCheckpointStorage(tmp_path / "checkpoints")
    rehydrated = make_workflow(fixture_repo, restarted_storage)
    requests = {}
    async for event in rehydrated.run(
        checkpoint_id=latest.checkpoint_id, stream=True
    ):
        if event.type == "request_info":
            assert isinstance(event.data, ApprovalBundle)
            requests[event.request_id] = ApprovalDecision(approved=True)

    assert requests
    output = None
    async for event in rehydrated.run(stream=True, responses=requests):
        if event.type == "output":
            output = event.data
    assert output.kind == DispositionKind.ANSWER_READY


async def test_provider_answer_without_claims_is_blocked(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class UnsupportedReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"An unsupported factual answer.",'
                    '"claims":[],"answer_claim_indices":[]}'
                )
            return "{}"

    storage = FileCheckpointStorage(tmp_path / "checkpoints")
    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        UnsupportedReasoner(),
        storage,
    )
    output = None
    request_seen = False
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "request_info":
            request_seen = True
        if event.type == "output":
            output = event.data

    assert not request_seen
    assert output.kind == DispositionKind.BLOCKED
    assert {finding.code for finding in output.review.findings} >= {
        "no_supported_claims",
        "unsupported_short_answer",
    }


async def test_provider_answer_is_replaced_by_skeptic_accepted_claims(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class ReviewedReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"The permit was approved.",'
                    '"claims":[{"text":"The commission continued the hearing.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The minutes do not establish approval."}],'
                    '"answer_claim_indices":[0]}'
                )
            if role_id == "skeptic":
                return '{"accepted":true,"findings":[]}'
            return "{}"

    storage = FileCheckpointStorage(tmp_path / "checkpoints")
    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        ReviewedReasoner(),
        storage,
    )
    requests = {}
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "request_info":
            requests[event.request_id] = ApprovalDecision(approved=True)
    output = None
    async for event in workflow.run(stream=True, responses=requests):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.short_answer == "The commission continued the hearing."


async def test_skeptic_rejection_returns_to_analyst_for_bounded_revision(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class RevisingReasoner:
        analyst_calls = 0
        skeptic_calls = 0

        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                request = json.loads(prompt.splitlines()[-1])
                self.analyst_calls += 1
                if self.analyst_calls == 1:
                    assert not request["prior_skeptic_findings"]
                    answer = "The permit was approved."
                else:
                    assert (
                        request["prior_skeptic_findings"][0]["code"] == "overclaim"
                    )
                    answer = "The commission continued the hearing."
                return (
                    f'{{"short_answer":"{answer}",'
                    f'"claims":[{{"text":"{answer}",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The minutes do not establish approval."}],'
                    '"answer_claim_indices":[0]}'
                )
            if role_id == "skeptic":
                self.skeptic_calls += 1
                if self.skeptic_calls == 1:
                    return (
                        '{"accepted":false,"findings":[{"severity":"error",'
                        '"code":"overclaim","message":"Approval is not established.",'
                        '"claim_index":0}]}'
                    )
                return '{"accepted":true,"findings":[]}'
            return "{}"

    reasoner = RevisingReasoner()
    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        reasoner,
        FileCheckpointStorage(tmp_path / "checkpoints"),
    )
    requests = {}
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "request_info":
            requests[event.request_id] = ApprovalDecision(approved=True)
    output = None
    async for event in workflow.run(stream=True, responses=requests):
        if event.type == "output":
            output = event.data

    assert reasoner.analyst_calls == 2
    assert reasoner.skeptic_calls == 2
    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.short_answer == "The commission continued the hearing."


async def test_provider_answer_retains_curated_research_gaps(
    fixture_repo: Path, tmp_path: Path
) -> None:
    database = (
        fixture_repo
        / "captures"
        / "cases"
        / "TEST-CASE"
        / "casebook.sqlite"
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE question_gaps "
            "(id INTEGER PRIMARY KEY, question_id TEXT, deciding_record TEXT)"
        )
        connection.execute(
            "INSERT INTO question_gaps (question_id, deciding_record) VALUES (?, ?)",
            ("hearing-action", "The final signed hearing order"),
        )

    class GroundedReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"The commission continued the hearing.",'
                    '"claims":[{"text":"The commission continued the hearing.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The minutes do not establish approval."}],'
                    '"answer_claim_indices":[0]}'
                )
            if role_id == "skeptic":
                return '{"accepted":true,"findings":[]}'
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        GroundedReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(
            case_id="TEST-CASE",
            question="What did the commission do at the hearing?",
        ),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.gaps[0].deciding_record == "The final signed hearing order"


async def test_persistent_skeptic_rejection_blocks_after_two_revisions(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class RejectingReasoner:
        analyst_calls = 0
        skeptic_calls = 0

        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                self.analyst_calls += 1
                return (
                    '{"short_answer":"The permit was approved.",'
                    '"claims":[{"text":"The permit was approved.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"Nothing further."}],'
                    '"answer_claim_indices":[0]}'
                )
            if role_id == "skeptic":
                self.skeptic_calls += 1
                return (
                    '{"accepted":false,"findings":[{"severity":"error",'
                    '"code":"overclaim","message":"Approval is not established.",'
                    '"claim_index":0}]}'
                )
            return "{}"

    reasoner = RejectingReasoner()
    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        reasoner,
        FileCheckpointStorage(tmp_path / "checkpoints"),
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert reasoner.analyst_calls == 3
    assert reasoner.skeptic_calls == 3
    assert output.kind == DispositionKind.BLOCKED


async def test_unchanged_monitor_stops_without_approval(
    fixture_repo: Path, tmp_path: Path
) -> None:
    storage = FileCheckpointStorage(tmp_path / "checkpoints")
    workflow = make_workflow(fixture_repo, storage)
    output = None
    request_seen = False
    async for event in workflow.run(
        MonitorObservation(
            monitor_id="planning-commission",
            observed_at="2026-08-21T12:00:00Z",
            summary="Monitor detected no record changes.",
            change_count=0,
        ),
        stream=True,
    ):
        request_seen = request_seen or event.type == "request_info"
        if event.type == "output":
            output = event.data

    assert not request_seen
    assert output.kind == DispositionKind.NO_CHANGE
