from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from mendo_agents.models import EvidenceGap
from mendo_agents.research_queue import ResearchQueue


def test_research_queue_deduplicates_by_case_and_record(tmp_path) -> None:
    queue = ResearchQueue(tmp_path / "research-queue.sqlite")
    gap = EvidenceGap(
        description="The plan adoption history is incomplete.",
        deciding_record="Resolution 2020-269 and later amendments",
        likely_custodian="MCCSD",
    )

    first = queue.enqueue("CASE-1", "What is operative?", (gap,))
    second = queue.enqueue("CASE-1", "Is this still current?", (gap,))

    assert first[0].id == second[0].id
    with sqlite3.connect(queue.path) as connection:
        row = connection.execute(
            "SELECT status, occurrence_count FROM research_queue"
        ).fetchone()
    assert row == ("triage", 2)


def test_json_research_queue_persists_and_deduplicates(tmp_path) -> None:
    path = tmp_path / "research-queue.json"
    gap = EvidenceGap(
        description="The operating permit is missing.",
        deciding_record="November 26, 2025 DDW permit",
        likely_custodian="DDW",
    )

    first = ResearchQueue(path).enqueue("CASE-1", "What is authorized?", (gap,))
    second = ResearchQueue(path).enqueue("CASE-1", "What changed?", (gap,))

    assert first[0].id == second[0].id
    state = json.loads(path.read_text(encoding="utf-8"))
    assert state[first[0].id]["status"] == "triage"
    assert state[first[0].id]["occurrence_count"] == 2

    ResearchQueue(path).enqueue(
        "CASE-1",
        "Why is another record needed?",
        (gap,),
        origin_run_id="json-question",
        provenance_snapshot={
            "schema_version": 1,
            "disposition": "answer_ready",
        },
    )
    state = json.loads(path.read_text(encoding="utf-8"))
    assert state["__question_runs__"]["json-question"][
        "provenance_snapshot"
    ]["disposition"] == "answer_ready"


def test_research_queue_persists_semantic_question_provenance(
    tmp_path,
) -> None:
    queue = ResearchQueue(tmp_path / "research-queue.sqlite")
    gap = EvidenceGap(
        description="The cited order does not identify the approved site.",
        deciding_record="Project-specific approval",
        likely_custodian="Public Agency",
        rationale=(
            "The general order authorizes a program but does not identify "
            "this project."
        ),
        related_claim_indices=(0,),
    )
    snapshot = {
        "schema_version": 1,
        "disposition": "answer_ready",
        "analysis": {
            "claims": [{"text": "The general order authorizes the program."}]
        },
    }

    queue.enqueue(
        "CASE-1",
        "Was this project approved?",
        (gap,),
        origin_run_id="question-1",
        provenance_snapshot=snapshot,
    )

    with sqlite3.connect(queue.path) as connection:
        analysis = connection.execute(
            """
            SELECT schema_version, result_json
              FROM research_question_analyses
             WHERE question_run_id = 'question-1'
            """
        ).fetchone()
        relationship = connection.execute(
            """
            SELECT rationale, related_claim_indices_json
              FROM research_question_run_gaps
             WHERE run_id = 'question-1'
            """
        ).fetchone()
    assert analysis[0] == 1
    assert json.loads(analysis[1]) == snapshot
    assert relationship == (gap.rationale, "[0]")


def test_json_queue_serializes_concurrent_question_snapshots(tmp_path) -> None:
    queue = ResearchQueue(tmp_path / "research-queue.json")

    def write_snapshot(index: int) -> None:
        queue.enqueue(
            "CASE-1",
            f"Question {index}",
            (),
            origin_run_id=f"run-{index}",
            provenance_snapshot={
                "schema_version": 1,
                "disposition": "answer_ready",
            },
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        tuple(executor.map(write_snapshot, range(40)))

    state = json.loads(queue.path.read_text(encoding="utf-8"))
    assert len(state["__question_runs__"]) == 40
