from __future__ import annotations

import argparse
from pathlib import Path

from mendo_agents.chat import PublicChatError, PublicChatService, _settings_from_args
from mendo_agents.config import Settings
from mendo_agents.models import (
    DispositionKind,
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
    }


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


def test_blocked_chat_exposes_safe_review_without_rejected_draft(
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
        review=SkepticReview(
            accepted=False,
            findings=(
                SkepticFinding(
                    severity="error",
                    code="unsupported_synthesis",
                    message="The conclusion is not established by the cited record.",
                ),
            ),
        ),
    )

    result = service._serialize(output)

    assert result["answer"] is None
    assert result["claims"] == []
    assert result["review_findings"] == [
        {
            "severity": "error",
            "code": "unsupported_synthesis",
            "message": "The conclusion is not established by the cited record.",
            "claim_index": None,
        }
    ]


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
