from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from mendo_agents.models import EvidenceGap
from mendo_agents.research_dispatch import ResearchDirectiveStore
from mendo_agents.research_queue import ResearchQueue
from mendo_agents.research_triage import (
    FoundryTriageWorker,
    TriagePlan,
    ResearchTriageStore,
)


class Reasoner:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls = 0

    async def respond(
        self,
        _role_id: str,
        _instructions: str,
        _prompt: str,
    ) -> str:
        self.calls += 1
        return json.dumps(self.response)


def enqueue_question(path: Path, run_id: str = "question-1") -> tuple[str, ...]:
    queued = ResearchQueue(path).enqueue(
        "CASE-1",
        "What official record decides the issue?",
        (
            EvidenceGap(
                description="The final policy is missing.",
                deciding_record="Final agency policy",
                likely_custodian="Example Agency",
            ),
            EvidenceGap(
                description="The approving resolution is missing.",
                deciding_record="Signed approving resolution",
                likely_custodian="Example Agency",
            ),
        ),
        origin_run_id=run_id,
        origin_type="foundry_public_chat",
        initiating_actor="public_cio",
    )
    return tuple(item.id for item in queued)


async def test_triage_prepares_one_bounded_directive(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite"
    lead_ids = enqueue_question(path)
    store = ResearchTriageStore(path)
    reasoner = Reasoner(
        {
            "disposition": "prepare_search",
            "rationale": "The records share one custodian and approval chain.",
            "title": "Find final policy and resolution",
            "search_brief": (
                "Retrieve the final policy and signed approving resolution "
                "from the agency's official archive."
            ),
            "allowed_hosts": ["records.example.gov"],
        }
    )
    worker = FoundryTriageWorker(
        store,
        reasoner,
        provider="scripted",
        allowed_hosts=("records.example.gov",),
    )

    assert await worker.process_one() is True

    directives = ResearchDirectiveStore(path).list()
    assert len(directives) == 1
    assert directives[0].status == "pending_approval"
    assert directives[0].lead_ids == tuple(sorted(lead_ids))
    with sqlite3.connect(path) as connection:
        statuses = connection.execute(
            "SELECT DISTINCT status FROM research_queue"
        ).fetchall()
        association = connection.execute(
            """
            SELECT question_run_id
              FROM research_directive_question_runs
             WHERE directive_id = ?
            """,
            (directives[0].id,),
        ).fetchone()
        triage = connection.execute(
            "SELECT status FROM research_triage_runs"
        ).fetchone()
    assert statuses == [("directive_pending",)]
    assert association == ("question-1",)
    assert triage == ("completed",)


async def test_triage_rejects_unapproved_host_without_advancing_gap(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queue.sqlite"
    enqueue_question(path)
    store = ResearchTriageStore(path)
    reasoner = Reasoner(
        {
            "disposition": "prepare_search",
            "rationale": "Search for the policy.",
            "title": "Find policy",
            "search_brief": "Retrieve the policy.",
            "allowed_hosts": ["untrusted.example.com"],
        }
    )
    worker = FoundryTriageWorker(
        store,
        reasoner,
        provider="scripted",
        allowed_hosts=("records.example.gov",),
    )

    assert await worker.process_one() is False
    assert await worker.process_one() is False
    assert await worker.process_one() is False
    assert await worker.process_one() is False
    assert reasoner.calls == 3

    with sqlite3.connect(path) as connection:
        statuses = connection.execute(
            "SELECT DISTINCT status FROM research_queue"
        ).fetchall()
        triage = connection.execute(
            """
            SELECT status, error_type
              FROM research_triage_runs
             ORDER BY id DESC
             LIMIT 1
            """
        ).fetchone()
        run_count = connection.execute(
            "SELECT COUNT(*) FROM research_triage_runs"
        ).fetchone()[0]
        heartbeat = connection.execute(
            "SELECT state, last_error FROM research_triage_worker_status"
        ).fetchone()
    assert statuses == [("triage",)]
    assert triage == ("failed", "ResearchTriageOutputError")
    assert run_count == 3
    assert heartbeat[0] == "failed"
    assert "unapproved hosts" in heartbeat[1]


async def test_triage_pauses_at_pending_approval_cap(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite"
    first_leads = enqueue_question(path, "question-1")
    directive_store = ResearchDirectiveStore(path)
    directive_store.create(
        "CASE-1",
        "Existing search",
        "Retrieve the existing record.",
        first_leads,
        ("records.example.gov",),
        question_run_id="question-1",
    )
    enqueue_question(path, "question-2")
    store = ResearchTriageStore(path)
    reasoner = Reasoner(
        {
            "disposition": "corpus_analysis_ready",
            "rationale": "The record is already present.",
        }
    )
    worker = FoundryTriageWorker(
        store,
        reasoner,
        provider="scripted",
        allowed_hosts=("records.example.gov",),
        max_pending_directives=1,
    )

    assert await worker.process_one() is False
    assert reasoner.calls == 0
    with sqlite3.connect(path) as connection:
        state = connection.execute(
            "SELECT state FROM research_triage_worker_status"
        ).fetchone()[0]
    assert state == "waiting_for_cio"


async def test_triage_rolls_back_directive_when_completion_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "queue.sqlite"
    enqueue_question(path)
    store = ResearchTriageStore(path)
    reasoner = Reasoner(
        {
            "disposition": "prepare_search",
            "rationale": "The official records share one custodian.",
            "title": "Find official records",
            "search_brief": "Retrieve the final policy and resolution.",
            "allowed_hosts": ["records.example.gov"],
        }
    )
    worker = FoundryTriageWorker(
        store,
        reasoner,
        provider="scripted",
        allowed_hosts=("records.example.gov",),
    )
    original = worker.directive_store.create_in_transaction

    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("simulated failure after directive insert")

    monkeypatch.setattr(
        worker.directive_store,
        "create_in_transaction",
        fail_after_insert,
    )

    assert await worker.process_one() is False

    with sqlite3.connect(path) as connection:
        directive_count = connection.execute(
            "SELECT COUNT(*) FROM research_directives"
        ).fetchone()[0]
        statuses = connection.execute(
            "SELECT DISTINCT status FROM research_queue"
        ).fetchall()
        triage_status = connection.execute(
            "SELECT status FROM research_triage_runs"
        ).fetchone()[0]
    assert directive_count == 0
    assert statuses == [("triage",)]
    assert triage_status == "failed"


async def test_triage_times_out_hung_foundry_call(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite"
    enqueue_question(path)
    store = ResearchTriageStore(path)

    class SlowReasoner:
        calls = 0

        async def respond(self, _role_id, _instructions, _prompt):
            self.calls += 1
            await asyncio.sleep(1)
            return "{}"

    reasoner = SlowReasoner()
    worker = FoundryTriageWorker(
        store,
        reasoner,
        provider="scripted",
        allowed_hosts=("records.example.gov",),
        request_timeout_seconds=0.02,
        heartbeat_seconds=0.005,
    )

    assert await worker.process_one() is False
    assert await worker.process_one() is False
    assert reasoner.calls == 1

    with sqlite3.connect(path) as connection:
        error, failure_class, retry_after = connection.execute(
            """
            SELECT error, failure_class, retry_after
              FROM research_triage_runs
            """
        ).fetchone()
        worker_state = connection.execute(
            "SELECT state FROM research_triage_worker_status"
        ).fetchone()[0]
    assert "exceeded the configured request timeout" in error
    assert failure_class == "transient"
    assert retry_after is not None
    assert worker_state == "retry_backoff"


def test_triage_scheduler_alternates_newest_and_oldest(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite"
    enqueue_question(path, "old-question")
    ResearchQueue(path).enqueue(
        "CASE-1",
        "Newest question",
        (
            EvidenceGap(
                description="A newer record is missing.",
                deciding_record="Newer final record",
                likely_custodian="Example Agency",
            ),
        ),
        origin_run_id="new-question",
    )
    store = ResearchTriageStore(path)

    newest = store.next_question()
    assert newest is not None
    assert newest.run_id == "new-question"
    first_run = store.start(newest, "scripted", None)
    store.apply_plan(
        first_run,
        newest,
        TriagePlan(
            disposition="requires_transaction_identification",
            rationale="A specific transaction is required.",
        ),
        ResearchDirectiveStore(path),
        3,
    )

    oldest = store.next_question()
    assert oldest is not None
    assert oldest.run_id == "old-question"
