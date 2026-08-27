from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pypdf import PdfWriter

from mendo_agents.models import (
    EvidenceGap,
    NegativeSearchFinding,
    ScoutSearchReport,
    SearchCandidate,
    StagedDownload,
)
from mendo_agents.repository import CorpusRepository
from mendo_agents.research_dispatch import (
    FoundryWebSearchScout,
    ResearchDirectiveStore,
    ResearchDispatchError,
    ResearchDispatcher,
)
from mendo_agents.research_queue import ResearchQueue


def make_queue(tmp_path: Path) -> tuple[ResearchQueue, str]:
    queue = ResearchQueue(tmp_path / "research-queue.sqlite")
    lead = queue.enqueue(
        "CASE-1",
        "What is the operative rule?",
        (
            EvidenceGap(
                description="The final policy is missing.",
                deciding_record="Final outside-agency service policy",
                likely_custodian="Example LAFCo",
            ),
        ),
        origin_type="foundry_public_chat",
        origin_run_id="run-1",
        initiating_actor="public_cio",
    )[0]
    return queue, lead.id


def make_corpus(tmp_path: Path) -> CorpusRepository:
    database = tmp_path / "captures" / "cases" / "CASE-1" / "casebook.sqlite"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, sha256 TEXT)"
        )
    return CorpusRepository(tmp_path, "CASE-1")


def report() -> ScoutSearchReport:
    return ScoutSearchReport(
        summary="Found the final policy.",
        candidates=(
            SearchCandidate(
                target_id="official-policy",
                url="https://records.example.gov/policy.pdf",
                issuing_body="Example LAFCo",
                title="Final Outside Agency Service Policy",
                relevance="Directly answers the directive.",
                establishes=("The final procedure.",),
                does_not_establish=("Compliance in a particular case.",),
                document_date="2026-01-01",
                version="final",
                signature_status="signed",
            ),
        ),
        negative_findings=(
            NegativeSearchFinding(
                repository="Example archive",
                query="older versions",
                result="No older version located.",
                limitation="The archive search is not proof of nonexistence.",
            ),
        ),
        citations=("https://records.example.gov/policy.pdf",),
        provider="scripted_web_search",
        model="fixture",
    )


def test_approved_directive_stages_validated_review_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue, lead_id = make_queue(tmp_path)
    store = ResearchDirectiveStore(queue.path)
    directive = store.create(
        "CASE-1",
        "Find final policy",
        "Locate the signed final outside-agency service policy.",
        (lead_id,),
        ("records.example.gov",),
    )
    assert directive.status == "pending_approval"
    assert store.approve(directive.id, "cio").status == "approved"

    class Scout:
        def search(self, _directive):
            return report()

    def fake_fetch(self, candidate, staging_directory):
        staging_directory.mkdir(parents=True, exist_ok=True)
        path = staging_directory / "official-policy.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with path.open("wb") as stream:
            writer.write(stream)
        return StagedDownload(
            candidate=candidate,
            status="captured_staged",
            attempted_at="2026-08-24T07:00:00+00:00",
            http_status=200,
            staging_path=str(path),
            final_url=candidate.url,
        )

    monkeypatch.setattr(
        "mendo_agents.research_dispatch.PublicRecordFetcher.fetch",
        fake_fetch,
    )
    result = ResearchDispatcher(
        store,
        Scout(),
        make_corpus(tmp_path),
        tmp_path / "research-staging",
    ).dispatch(directive.id)

    bundle_path = Path(result["review_bundle_path"])
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert payload["directive_id"] == directive.id
    assert payload["candidates"][0]["id"] == "official-policy"
    assert store.get(directive.id).status == "completed"
    with sqlite3.connect(queue.path) as connection:
        status = connection.execute(
            "SELECT status FROM research_queue WHERE id = ?", (lead_id,)
        ).fetchone()[0]
    assert status == "candidate_staged"


def test_directive_requires_explicit_approval(tmp_path: Path) -> None:
    queue, lead_id = make_queue(tmp_path)
    store = ResearchDirectiveStore(queue.path)
    directive = store.create(
        "CASE-1",
        "Find final policy",
        "Locate the signed policy.",
        (lead_id,),
        ("records.example.gov",),
    )

    with pytest.raises(ResearchDispatchError, match="approved exactly once"):
        store.start(directive.id)


def test_interrupted_dispatch_returns_to_approved_retry(
    tmp_path: Path,
) -> None:
    queue, lead_id = make_queue(tmp_path)
    store = ResearchDirectiveStore(queue.path)
    directive = store.create(
        "CASE-1",
        "Find final policy",
        "Locate the signed policy.",
        (lead_id,),
        ("records.example.gov",),
    )
    store.approve(directive.id, "cio")
    run_id = store.start(directive.id)

    assert store.recover_interrupted_dispatches() == 1

    assert store.get(directive.id).status == "approved"
    run = store.runs(directive.id)[0]
    assert run["id"] == run_id
    assert run["status"] == "failed"
    assert run["error_type"] == "WorkbenchRestart"
    with sqlite3.connect(queue.path) as connection:
        status = connection.execute(
            "SELECT status FROM research_queue WHERE id = ?",
            (lead_id,),
        ).fetchone()[0]
    assert status == "directive_approved"


def test_terminal_dispatch_failure_invokes_recovery(
    tmp_path: Path,
) -> None:
    queue, lead_id = make_queue(tmp_path)
    store = ResearchDirectiveStore(queue.path)
    directive = store.create(
        "CASE-1",
        "Find final policy",
        "Locate the signed policy.",
        (lead_id,),
        ("records.example.gov",),
    )
    store.approve(directive.id, "cio")

    class FailingScout:
        def search(self, _directive):
            raise ResearchDispatchError("Foundry returned malformed output")

    class Recovery:
        run_ids: list[int] = []

        def diagnose(self, run_id):
            self.run_ids.append(run_id)

    recovery = Recovery()
    with pytest.raises(
        ResearchDispatchError, match="Foundry returned malformed output"
    ):
        ResearchDispatcher(
            store,
            FailingScout(),
            make_corpus(tmp_path),
            tmp_path / "research-staging",
            failure_recovery=recovery,
        ).dispatch(directive.id)

    assert len(recovery.run_ids) == 1
    run = store.runs(directive.id)[0]
    assert run["id"] == recovery.run_ids[0]
    assert run["status"] == "failed"
    assert run["error_type"] == "ResearchDispatchError"


def test_foundry_report_rejects_uncited_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.test/project")
    monkeypatch.setenv("FOUNDRY_MODEL", "test-model")
    scout = FoundryWebSearchScout()
    raw = json.dumps(
        {
            "summary": "Found one.",
            "candidates": [
                {
                    "target_id": "invented",
                    "url": "https://records.example.gov/invented.pdf",
                    "issuing_body": "Example",
                    "title": "Invented",
                    "relevance": "Claimed relevant.",
                    "establishes": ["Nothing verified."],
                    "does_not_establish": ["Everything."],
                }
            ],
            "negative_findings": [],
        }
    )

    with pytest.raises(ResearchDispatchError, match="lacks a Foundry citation"):
        scout._parse(raw, ())


def test_foundry_report_accepts_only_exact_cited_candidate_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.test/project")
    monkeypatch.setenv("FOUNDRY_MODEL", "test-model")
    scout = FoundryWebSearchScout()
    url = "https://records.example.gov/final.pdf"
    raw = json.dumps(
        {
            "summary": "Found the final record.",
            "candidates": [
                {
                    "target_id": "final-record",
                    "url": url,
                    "issuing_body": "Example",
                    "title": "Final record",
                    "relevance": "Direct record.",
                    "establishes": ["Its own contents."],
                    "does_not_establish": ["Compliance."],
                }
            ],
            "negative_findings": [],
        }
    )

    report = scout._parse(raw, (f"{url}#page=1",))
    assert report.candidates[0].url == url


def test_queue_records_prompt_origin(tmp_path: Path) -> None:
    queue, lead_id = make_queue(tmp_path)
    with sqlite3.connect(queue.path) as connection:
        row = connection.execute(
            """
            SELECT origin_type, origin_run_id, initiating_actor
              FROM research_queue
             WHERE id = ?
            """,
            (lead_id,),
        ).fetchone()
    assert row == ("foundry_public_chat", "run-1", "public_cio")
