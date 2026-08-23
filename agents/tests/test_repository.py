from __future__ import annotations

import sqlite3

from mendo_agents.models import EvidenceLocator
from mendo_agents.repository import CorpusRepository, NodeCommandAdapter


def test_search_and_locator_validation(fixture_repo) -> None:
    corpus = CorpusRepository(fixture_repo, "TEST-CASE")

    hits = corpus.search("What did the commission continue?")

    assert hits[0].document_id == "minutes"
    assert hits[0].page == 4
    assert corpus.validate_locator(EvidenceLocator("minutes", page=4))
    assert not corpus.validate_locator(EvidenceLocator("minutes", page=99))
    assert not corpus.validate_locator(EvidenceLocator("missing", page=4))


def test_search_returns_timestamped_transcript_hits(fixture_repo) -> None:
    corpus = CorpusRepository(fixture_repo, "TEST-CASE")

    hits = corpus.search("coastal groundwater guideline adverse drawdown")
    transcript = next(hit for hit in hits if hit.timestamp)

    assert transcript.document_id == "minutes"
    assert transcript.page is None
    assert transcript.timestamp == "01:15:47-01:15:52"
    assert "groundwater guideline" in corpus.hit_text(transcript)
    assert corpus.validate_locator(
        EvidenceLocator("minutes", timestamp=transcript.timestamp)
    )


def test_timestamp_text_includes_every_overlapping_segment(fixture_repo) -> None:
    database = (
        fixture_repo
        / "captures"
        / "cases"
        / "TEST-CASE"
        / "casebook.sqlite"
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO transcript_segments VALUES (?, ?, ?, ?, ?)",
            ("minutes", 1, 4553.0, 4558.0, "The discussion then addressed limits."),
        )

    text = CorpusRepository(fixture_repo, "TEST-CASE").timestamp_text(
        "minutes", "01:15:47-01:15:58"
    )

    assert text == (
        "The coastal groundwater guideline defines adverse drawdown. "
        "The discussion then addressed limits."
    )


def test_curated_analysis_preserves_multiple_page_locators(fixture_repo) -> None:
    database = (
        fixture_repo
        / "captures"
        / "cases"
        / "TEST-CASE"
        / "casebook.sqlite"
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE claims SET locator = 'pages 4, 7'")

    analysis = CorpusRepository(fixture_repo, "TEST-CASE").curated_analysis(
        "What did the commission do at the hearing?"
    )

    assert analysis is not None
    assert analysis.claims[0].locators == (
        EvidenceLocator("minutes", page=4),
        EvidenceLocator("minutes", page=7),
    )


def test_curated_analysis_matches_long_conversational_question(fixture_repo) -> None:
    analysis = CorpusRepository(fixture_repo, "TEST-CASE").curated_analysis(
        "I am trying to understand the broader timeline and legal consequences; "
        "what did the commission do at the hearing, and how should that action be "
        "understood alongside all the other records?"
    )

    assert analysis is not None
    assert analysis.short_answer == (
        "The commission continued the hearing to September 3."
    )


def test_node_adapter_rejects_unlisted_commands(fixture_repo) -> None:
    adapter = NodeCommandAdapter(fixture_repo)

    try:
        adapter.run("arbitrary_shell")
    except ValueError as error:
        assert "not allowlisted" in str(error)
    else:
        raise AssertionError("Unlisted command was accepted")
