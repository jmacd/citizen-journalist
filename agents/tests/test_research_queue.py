from __future__ import annotations

import json
import sqlite3

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
