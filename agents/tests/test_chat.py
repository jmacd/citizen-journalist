from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from mendo_agents.chat import PublicChatError, PublicChatService, _settings_from_args
from mendo_agents.config import Settings
from mendo_agents.models import (
    Analysis,
    Claim,
    Confidence,
    DispositionKind,
    EvidenceGap,
    EvidenceLocator,
    RunDisposition,
    SkepticFinding,
    SkepticReview,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_chat_cli_preserves_configured_research_queue_path(
    fixture_repo: Path, monkeypatch
) -> None:
    path = fixture_repo / "durable" / "research-queue.json"
    monkeypatch.setenv("MENDO_RESEARCH_QUEUE_PATH", str(path))

    settings = _settings_from_args(
        argparse.Namespace(
            repo_root=fixture_repo,
            case_id=None,
            provider=None,
            host="127.0.0.1",
            port=4173,
        )
    )

    assert settings.research_queue_path == path


async def test_public_chat_returns_skeptic_checked_citations(
    fixture_repo: Path, tmp_path: Path
) -> None:
    service = PublicChatService(
        Settings(
            repo_root=fixture_repo,
            case_id="TEST-CASE",
            checkpoint_root=tmp_path / "checkpoints",
            run_root=tmp_path / "runs",
        ),
        policy_path=REPO_ROOT / "agents/organization/society.yaml",
    )

    result = await service.ask("Did the commission continue the hearing?")

    assert result["status"] == "answer_ready"
    assert result["answer"] == (
        "The commission continued the hearing to September 3."
    )
    assert result["runtime"] == {
        "provider": "scripted",
        "model": None,
        "label": "Scripted evidence mode (no LLM)",
    }
    assert result["claims"][0]["citations"][0] == {
        "document_id": "minutes",
        "title": "Planning Commission Minutes",
        "publisher": "Mendocino County",
        "document_date": "2026-08-20",
        "url": "https://example.gov/minutes.pdf",
        "page": 4,
        "section": None,
        "timestamp": None,
        "field": None,
        "invalid": False,
    }
    with sqlite3.connect(service.research_queue.path) as connection:
        row = connection.execute(
            """
            SELECT r.question, a.result_json
              FROM research_question_runs r
              JOIN research_question_analyses a
                ON a.question_run_id = r.id
            """
        ).fetchone()
    snapshot = json.loads(row[1])
    assert row[0] == "Did the commission continue the hearing?"
    assert snapshot["analysis"]["claims"][0]["text"] == (
        "The commission continued the hearing."
    )
    assert snapshot["review"]["accepted"] is True
    assert snapshot["conversation_context"] == []


async def test_public_chat_rejects_empty_questions(
    fixture_repo: Path, tmp_path: Path
) -> None:
    service = PublicChatService(
        Settings(
            repo_root=fixture_repo,
            case_id="TEST-CASE",
            checkpoint_root=tmp_path / "checkpoints",
            run_root=tmp_path / "runs",
        ),
        policy_path=REPO_ROOT / "agents/organization/society.yaml",
    )

    try:
        await service.ask(" \n ")
    except PublicChatError as error:
        assert str(error) == "Enter a question about this case."
    else:
        raise AssertionError("Empty public question was accepted")


def test_blocked_chat_exposes_labeled_draft_context_and_targeted_gap(
    fixture_repo: Path, tmp_path: Path
) -> None:
    service = PublicChatService(
        Settings(
            repo_root=fixture_repo,
            case_id="TEST-CASE",
            checkpoint_root=tmp_path / "checkpoints",
            run_root=tmp_path / "runs",
        ),
        policy_path=REPO_ROOT / "agents/organization/society.yaml",
    )
    output = RunDisposition(
        kind=DispositionKind.BLOCKED,
        summary="The Skeptic blocked publication.",
        analysis=Analysis(
            short_answer="The commission may have approved the service.",
            claims=(
                Claim(
                    text="The commission approved the service.",
                    confidence=Confidence.SUPPORTED_INTERPRETATION,
                    locators=(
                        EvidenceLocator(document_id="minutes", page=4),
                    ),
                    does_not_establish="The scope of approval.",
                ),
            ),
        ),
        review=SkepticReview(
            accepted=False,
            findings=(
                SkepticFinding(
                    severity="error",
                    code="unsupported_synthesis",
                    message="The conclusion is not established by the cited record.",
                    claim_index=0,
                ),
            ),
            targeted_gaps=(
                EvidenceGap(
                    description="Formal approval is missing.",
                    deciding_record="Signed approval resolution",
                ),
            ),
        ),
    )

    result = service._serialize(output)

    assert result["answer"] is None
    assert result["claims"] == []
    assert result["withheld_answer"] == (
        "The commission may have approved the service."
    )
    assert result["withheld_claims"][0]["text"] == (
        "The commission approved the service."
    )
    assert result["withheld_claims"][0]["citations"][0]["title"] == (
        "Planning Commission Minutes"
    )
    assert result["gaps"][0]["deciding_record"] == "Signed approval resolution"
    assert result["review_findings"] == [
        {
            "severity": "error",
            "code": "unsupported_synthesis",
            "message": "The conclusion is not established by the cited record.",
            "claim_index": 0,
            "claim_number": 1,
        }
    ]


def test_blocked_chat_labels_invalid_draft_locator(
    fixture_repo: Path, tmp_path: Path
) -> None:
    service = PublicChatService(
        Settings(
            repo_root=fixture_repo,
            case_id="TEST-CASE",
            checkpoint_root=tmp_path / "checkpoints",
            run_root=tmp_path / "runs",
        ),
        policy_path=REPO_ROOT / "agents/organization/society.yaml",
    )
    output = RunDisposition(
        kind=DispositionKind.BLOCKED,
        summary="The Skeptic blocked publication.",
        analysis=Analysis(
            short_answer="Unsupported draft.",
            claims=(
                Claim(
                    text="Unsupported claim.",
                    confidence=Confidence.UNRESOLVED,
                    locators=(
                        EvidenceLocator(document_id="invented-source", page=1),
                    ),
                    does_not_establish="Anything.",
                ),
            ),
        ),
        review=SkepticReview(
            accepted=False,
            findings=(
                SkepticFinding(
                    severity="error",
                    code="invalid_locator",
                    message="The document does not exist.",
                    claim_index=0,
                ),
            ),
        ),
    )

    result = service._serialize(output)

    citation = result["withheld_claims"][0]["citations"][0]
    assert citation["invalid"] is True
    assert citation["title"] == "Invalid evidence locator: invented-source"


def test_public_gaps_merge_claim_relationships_for_same_record() -> None:
    output = RunDisposition(
        kind=DispositionKind.ANSWER_READY,
        summary="A further record is needed.",
        gaps=(
            EvidenceGap(
                description="The project location is unresolved.",
                deciding_record="Project approval",
                rationale="The order does not identify the location.",
                related_claim_indices=(0,),
            ),
            EvidenceGap(
                description="The approving action is unresolved.",
                deciding_record="Project approval",
                rationale="The minutes do not contain the signed action.",
                related_claim_indices=(1,),
            ),
        ),
    )

    gaps = PublicChatService._public_gaps(output)

    assert len(gaps) == 1
    assert gaps[0].related_claim_indices == (0, 1)
    assert gaps[0].rationale == (
        "The order does not identify the location.\n"
        "The minutes do not contain the signed action."
    )


async def test_public_chat_uses_bounded_history_for_followup(
    fixture_repo: Path, tmp_path: Path
) -> None:
    service = PublicChatService(
        Settings(
            repo_root=fixture_repo,
            case_id="TEST-CASE",
            checkpoint_root=tmp_path / "checkpoints",
            run_root=tmp_path / "runs",
        ),
        policy_path=REPO_ROOT / "agents/organization/society.yaml",
    )

    result = await service.ask(
        "What does that mean?",
        history=(
            {
                "role": "user",
                "content": "What did the commission do at the hearing?",
            },
            {
                "role": "assistant",
                "content": "The commission continued the hearing.",
            },
        ),
    )

    assert result["status"] == "answer_ready"
    assert result["answer"] == (
        "The commission continued the hearing to September 3."
    )
