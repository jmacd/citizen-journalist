from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    case_id = "TEST-CASE"
    case_root = tmp_path / "cases" / case_id
    case_root.mkdir(parents=True)
    for filename in (
        "manifest.yaml",
        "acquisition-log.yaml",
        "authority-chain.yaml",
        "water-law.yaml",
        "questions.yaml",
        "records-requests.yaml",
    ):
        (case_root / filename).write_text("{}\n", encoding="utf-8")

    database_path = tmp_path / "captures" / "cases" / case_id / "casebook.sqlite"
    database_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE documents (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          publisher TEXT,
          document_date TEXT,
          url TEXT,
          attachment_url TEXT,
          status TEXT,
          sha256 TEXT
        );
        CREATE TABLE document_pages (
          document_id TEXT NOT NULL,
          page_number INTEGER NOT NULL,
          text TEXT NOT NULL,
          PRIMARY KEY (document_id, page_number)
        );
        CREATE VIRTUAL TABLE document_search USING fts5(
          document_id UNINDEXED,
          page_number UNINDEXED,
          title,
          publisher,
          text,
          tokenize = 'porter unicode61'
        );
        CREATE TABLE transcript_segments (
          document_id TEXT NOT NULL,
          segment_index INTEGER NOT NULL,
          start_seconds REAL NOT NULL,
          end_seconds REAL NOT NULL,
          text TEXT NOT NULL,
          PRIMARY KEY (document_id, segment_index)
        );
        CREATE VIRTUAL TABLE transcript_search USING fts5(
          document_id UNINDEXED,
          segment_index UNINDEXED,
          start_seconds UNINDEXED,
          end_seconds UNINDEXED,
          title,
          publisher,
          text,
          tokenize = 'porter unicode61'
        );
        CREATE TABLE questions (
          id TEXT PRIMARY KEY,
          question TEXT NOT NULL,
          status TEXT NOT NULL,
          short_answer TEXT
        );
        CREATE TABLE claims (
          id INTEGER PRIMARY KEY,
          question_id TEXT NOT NULL,
          claim TEXT NOT NULL,
          confidence TEXT,
          document_id TEXT,
          locator TEXT
        );
        INSERT INTO documents VALUES
          ('minutes', 'Planning Commission Minutes', 'Mendocino County',
           '2026-08-20', 'https://example.gov/minutes.pdf', NULL, 'captured',
           'abc123');
        INSERT INTO document_pages VALUES
          ('minutes', 4, 'The commission continued the hearing to September 3.');
        INSERT INTO document_search VALUES
          ('minutes', 4, 'Planning Commission Minutes', 'Mendocino County',
           'The commission continued the hearing to September 3.');
        INSERT INTO transcript_segments VALUES
          ('minutes', 0, 4547.0, 4552.0,
           'The coastal groundwater guideline defines adverse drawdown.');
        INSERT INTO transcript_search VALUES
          ('minutes', 0, 4547.0, 4552.0, 'Planning Commission Minutes',
           'Mendocino County',
           'The coastal groundwater guideline defines adverse drawdown.');
        INSERT INTO questions VALUES
          ('hearing-action',
           'What did the commission do at the hearing?',
           'answered',
           'The commission continued the hearing to September 3.');
        INSERT INTO claims
          (question_id, claim, confidence, document_id, locator)
        VALUES
          ('hearing-action',
           'The commission continued the hearing.',
           'verified_from_minutes',
           'minutes',
           'page 4');
        """
    )
    connection.close()

    skill_path = tmp_path / ".github" / "skills" / "answer-case-question"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text(
        "---\nname: answer-case-question\n---\nCite every claim.\n",
        encoding="utf-8",
    )
    return tmp_path
