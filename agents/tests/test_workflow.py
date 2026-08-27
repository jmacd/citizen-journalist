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
                "conclusion_kind": "affirmative",
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
                    '"claims":[],"answer_claim_indices":[],'
                    '"conclusion_kind":"affirmative"}'
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
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative"}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
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
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative"}'
                )
            if role_id == "skeptic":
                self.skeptic_calls += 1
                if self.skeptic_calls == 1:
                    return (
                        '{"accepted":false,"conclusion_kind_supported":true,'
                        '"findings":[{"severity":"error",'
                        '"code":"overclaim","message":"Approval is not established.",'
                        '"claim_index":0}]}'
                    )
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
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
                request = json.loads(prompt.splitlines()[-1])
                assert request["output_limits"]["maximum_claims"] == 6
                assert request["output_limits"]["maximum_gaps"] == 6
                assert "rules" not in request["requirements"]
                assert "watches" not in request["requirements"]
                assert "request_drafts" not in request["requirements"]
                return (
                    '{"short_answer":"The commission continued the hearing.",'
                    '"claims":[{"text":"The commission continued the hearing.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The minutes do not establish approval."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative"}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
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


async def test_public_analyst_repairs_invalid_json_once(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class RepairingReasoner:
        analyst_calls = 0

        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                self.analyst_calls += 1
                if self.analyst_calls == 1:
                    return '{"short_answer":"The commission continued'
                assert "Repair invalid Analyst JSON" in instructions
                return (
                    '{"short_answer":"The commission continued the hearing.",'
                    '"claims":[{"text":"The commission continued the hearing.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The final outcome."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative","gaps":[]}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
            return "{}"

    reasoner = RepairingReasoner()
    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        reasoner,
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert reasoner.analyst_calls == 2
    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.short_answer == "The commission continued the hearing."


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
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative"}'
                )
            if role_id == "skeptic":
                self.skeptic_calls += 1
                return (
                    '{"accepted":false,"conclusion_kind_supported":true,'
                    '"findings":[{"severity":"error",'
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


async def test_public_review_stops_after_one_revision(
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
                    '"does_not_establish":"The permit itself."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative","gaps":[]}'
                )
            if role_id == "skeptic":
                self.skeptic_calls += 1
                return (
                    '{"accepted":false,"conclusion_kind_supported":true,'
                    '"findings":[{"severity":"error",'
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
        auto_publish_read_only=True,
        max_review_revisions=1,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="Was it approved?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert reasoner.analyst_calls == 2
    assert reasoner.skeptic_calls == 2
    assert output.kind == DispositionKind.BLOCKED


async def test_skeptic_accepts_scoped_not_established_conclusion(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class BoundedNegativeReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                request = json.loads(prompt.splitlines()[-1])
                assert "not_established answer is a valid bounded conclusion" in (
                    request["bounded_negative_policy"]
                )
                assert "conclusion_kind" in request["requirements"]
                return (
                    '{"short_answer":"The reviewed minutes do not establish '
                    'that the permit was approved.",'
                    '"claims":[{"text":"The reviewed minutes do not establish '
                    'that the permit was approved.",'
                    '"confidence":"unresolved",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"That approval was prohibited or '
                    'that no approval exists elsewhere."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"not_established",'
                    '"scope_statement":"The registered corpus pages retrieved '
                    'for this question as of this run.",'
                    '"gaps":[]}'
                )
            if role_id == "skeptic":
                request = json.loads(prompt.splitlines()[-1])
                assert request["conclusion_kind"] == "not_established"
                assert request["scope_statement"]
                assert "without demanding proof of nonexistence" in prompt
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        BoundedNegativeReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="Was it approved?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.conclusion_kind == "not_established"
    assert output.analysis.short_answer == (
        "The reviewed minutes do not establish that the permit was approved."
    )


async def test_missing_bounded_negative_scope_blocks_normally(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class UnscopedReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"The records do not establish approval.",'
                    '"claims":[{"text":"The records do not establish approval.",'
                    '"confidence":"unresolved","document_id":"minutes","page":4,'
                    '"does_not_establish":"That approval was prohibited."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"not_established","gaps":[]}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        UnscopedReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
        max_review_revisions=0,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="Was it approved?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.BLOCKED
    assert {finding.code for finding in output.review.findings} == {
        "unbounded_negative_finding"
    }


async def test_rejected_unmapped_context_does_not_withhold_supported_answer(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class ContextRejectingReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"The records do not establish approval.",'
                    '"claims":['
                    '{"text":"The records do not establish approval.",'
                    '"confidence":"unresolved","document_id":"minutes","page":4,'
                    '"does_not_establish":"That approval was prohibited."},'
                    '{"text":"Approval always requires a second vote.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"Whether an exception applies."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"not_established",'
                    '"scope_statement":"The registered minutes reviewed in this run.",'
                    '"gaps":[]}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":false,"conclusion_kind_supported":true,'
                    '"findings":[{"severity":"error",'
                    '"code":"overclaim","message":"The second-vote rule is not '
                    'established.","claim_index":1}]}'
                )
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        ContextRejectingReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="Was it approved?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.ANSWER_READY
    assert output.analysis.answer_claim_indices == (0,)
    assert len(output.analysis.claims) == 2
    assert output.review.findings[0].severity == "warning"
    assert output.review.findings[0].code == "excluded_context_overclaim"


async def test_out_of_range_skeptic_claim_index_blocks_publication(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class MisindexedReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                return (
                    '{"short_answer":"The hearing continued.",'
                    '"claims":[{"text":"The hearing continued.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The final outcome."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative","gaps":[]}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":false,"conclusion_kind_supported":true,'
                    '"findings":[{"severity":"error","code":"overclaim",'
                    '"message":"The claim is unsupported.","claim_index":99}]}'
                )
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        MisindexedReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        auto_publish_read_only=True,
        max_review_revisions=0,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.BLOCKED
    assert {finding.code for finding in output.review.findings} == {
        "invalid_skeptic_output"
    }


async def test_rule_validation_error_cannot_be_downgraded_as_context(
    fixture_repo: Path, tmp_path: Path
) -> None:
    class InvalidRuleReasoner:
        async def respond(self, role_id, instructions, prompt):
            if role_id == "analyst":
                rule = (
                    '{"actor":"Commission","action":"continue a hearing",'
                    '"trigger":"a public vote","procedure":"vote at a meeting",'
                    '"geography":"Mendocino County",'
                    '"temporal_scope":"the cited meeting",'
                    '"effect":"continues the hearing",'
                    '"does_not_establish":"the final outcome",'
                    '"document_id":"minutes","page":4}'
                )
                invalid_rule = rule.replace(
                    '"document_id":"minutes"',
                    '"document_id":"missing-document"',
                )
                return (
                    '{"short_answer":"The hearing continued.",'
                    '"claims":[{"text":"The hearing continued.",'
                    '"confidence":"supported_interpretation",'
                    '"document_id":"minutes","page":4,'
                    '"does_not_establish":"The final outcome."}],'
                    '"answer_claim_indices":[0],'
                    '"conclusion_kind":"affirmative","gaps":[],'
                    f'"rules":[{rule},{invalid_rule}]}}'
                )
            if role_id == "skeptic":
                return (
                    '{"accepted":true,"conclusion_kind_supported":true,'
                    '"findings":[]}'
                )
            return "{}"

    workflow = build_evidence_workflow(
        CorpusRepository(fixture_repo, "TEST-CASE"),
        load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
        load_skills(fixture_repo),
        InvalidRuleReasoner(),
        FileCheckpointStorage(tmp_path / "checkpoints"),
        max_review_revisions=0,
    )
    output = None
    async for event in workflow.run(
        CaseQuestion(case_id="TEST-CASE", question="What happened?"),
        stream=True,
    ):
        if event.type == "output":
            output = event.data

    assert output.kind == DispositionKind.BLOCKED
    assert "rule_invalid_locator" in {
        finding.code for finding in output.review.findings
    }


def test_review_revision_budget_requires_enough_workflow_iterations(
    fixture_repo: Path, tmp_path: Path
) -> None:
    try:
        build_evidence_workflow(
            CorpusRepository(fixture_repo, "TEST-CASE"),
            load_society_policy(REPO_ROOT / "agents/organization/society.yaml"),
            load_skills(fixture_repo),
            ScriptedReasoner(),
            FileCheckpointStorage(tmp_path / "checkpoints"),
            max_iterations=10,
            max_review_revisions=2,
        )
    except ValueError as error:
        assert "minimum 11" in str(error)
    else:
        raise AssertionError("Unsafe workflow iteration budget was accepted")


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
