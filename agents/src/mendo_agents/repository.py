"""Read-only access to curated case data and the generated page corpus."""

from __future__ import annotations

import re
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import (
    Analysis,
    Claim,
    Confidence,
    CorpusHit,
    EvidenceGap,
    EvidenceLocator,
)


class CorpusUnavailableError(RuntimeError):
    pass


class CorpusRepository:
    def __init__(self, repo_root: Path, case_id: str) -> None:
        self.repo_root = repo_root.resolve()
        self.case_id = case_id
        self.database_path = (
            self.repo_root / "captures" / "cases" / case_id / "casebook.sqlite"
        )
        self.case_root = self.repo_root / "cases" / case_id

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.is_file():
            raise CorpusUnavailableError(
                f"Case database not found: {self.database_path}. "
                "Run npm run build:case-db first."
            )
        connection = sqlite3.connect(
            f"file:{self.database_path}?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _fts_query(text: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,}", text)
        unique = list(dict.fromkeys(token.lower() for token in tokens))
        if not unique:
            raise ValueError("Search text must contain at least one useful token")
        return " OR ".join(f'"{token.replace(chr(34), "")}"' for token in unique[:20])

    def search(self, text: str, limit: int = 20) -> list[CorpusHit]:
        query = self._fts_query(text)
        document_sql = """
            SELECT document_id, title, publisher, page_number,
                   snippet(document_search, 4, '[', ']', ' … ', 24) AS excerpt,
                   bm25(document_search) AS rank
              FROM document_search
             WHERE document_search MATCH ?
             ORDER BY rank
             LIMIT ?
        """
        transcript_sql = """
            SELECT document_id, title, publisher, start_seconds, end_seconds,
                   snippet(transcript_search, 6, '[', ']', ' … ', 32) AS excerpt,
                   bm25(transcript_search) AS rank
              FROM transcript_search
             WHERE transcript_search MATCH ?
             ORDER BY rank
             LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(document_sql, (query, limit)).fetchall()
            try:
                transcript_rows = connection.execute(
                    transcript_sql, (query, limit)
                ).fetchall()
            except sqlite3.OperationalError:
                transcript_rows = []
        hits = [
            CorpusHit(
                document_id=row["document_id"],
                title=row["title"],
                publisher=row["publisher"],
                page=row["page_number"],
                excerpt=row["excerpt"],
                rank=row["rank"],
            )
            for row in rows
        ]
        hits.extend(
            CorpusHit(
                document_id=row["document_id"],
                title=row["title"],
                publisher=row["publisher"],
                page=None,
                excerpt=row["excerpt"],
                rank=row["rank"],
                timestamp=(
                    f"{self._timestamp(row['start_seconds'])}-"
                    f"{self._timestamp(row['end_seconds'])}"
                ),
            )
            for row in transcript_rows
        )
        return sorted(hits, key=lambda hit: hit.rank)[:limit]

    @staticmethod
    def _timestamp(seconds: float) -> str:
        whole = max(0, int(seconds))
        hours, remainder = divmod(whole, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def hit_text(self, hit: CorpusHit) -> str:
        if hit.page is not None:
            return self.page_text(hit.document_id, hit.page)
        if hit.timestamp is None:
            return hit.excerpt
        return self.timestamp_text(hit.document_id, hit.timestamp)

    def timestamp_text(self, document_id: str, timestamp: str) -> str:
        start, separator, end = timestamp.partition("-")
        start_seconds = self._timestamp_seconds(start)
        end_seconds = self._timestamp_seconds(end if separator else start)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT text FROM transcript_segments
                 WHERE document_id = ?
                  AND end_seconds >= ?
                  AND start_seconds <= ?
                 ORDER BY start_seconds
                """,
                (document_id, start_seconds, end_seconds),
            ).fetchall()
        if not rows:
            raise KeyError(
                f"Unknown transcript locator: {document_id} timestamp {timestamp}"
            )
        return " ".join(str(row["text"]) for row in rows)

    @staticmethod
    def _timestamp_seconds(timestamp: str) -> int:
        parts = [int(part) for part in timestamp.split(":")]
        if len(parts) != 3:
            raise ValueError(f"Invalid timestamp locator: {timestamp}")
        return parts[0] * 3600 + parts[1] * 60 + parts[2]

    def page_text(self, document_id: str, page: int) -> str:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT text FROM document_pages
                 WHERE document_id = ? AND page_number = ?
                """,
                (document_id, page),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown document locator: {document_id} page {page}")
        return str(row["text"])

    def validate_locator(self, locator: EvidenceLocator) -> bool:
        if not locator.is_precise():
            return False
        with self._connect() as connection:
            document = connection.execute(
                "SELECT 1 FROM documents WHERE id = ?", (locator.document_id,)
            ).fetchone()
            if document is None:
                return False
            if locator.page is not None:
                page = connection.execute(
                    """
                    SELECT 1 FROM document_pages
                     WHERE document_id = ? AND page_number = ?
                    """,
                    (locator.document_id, locator.page),
                ).fetchone()
                return page is not None
        return True

    def document_by_hash(self, sha256: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE sha256 = ? LIMIT 1", (sha256,)
            ).fetchone()
        return str(row["id"]) if row else None

    def document_metadata(self, document_id: str) -> dict[str, str | None]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, publisher, document_date, url, attachment_url,
                       status
                  FROM documents
                 WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown document: {document_id}")
        return {key: row[key] for key in row.keys()}

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        }

    def curated_analysis(self, question: str) -> Analysis | None:
        query_tokens = self._tokens(question)
        if not query_tokens:
            return None
        with self._connect() as connection:
            try:
                questions = connection.execute(
                    "SELECT id, question, short_answer FROM questions"
                ).fetchall()
            except sqlite3.OperationalError:
                return None
            scored: list[tuple[float, sqlite3.Row]] = []
            for row in questions:
                candidate_tokens = self._tokens(row["question"])
                intersection = len(query_tokens & candidate_tokens)
                union = query_tokens | candidate_tokens
                jaccard = intersection / len(union) if union else 0
                candidate_coverage = (
                    intersection / len(candidate_tokens) if candidate_tokens else 0
                )
                score = (
                    max(jaccard, candidate_coverage * 0.8)
                    if intersection >= 3
                    else jaccard
                )
                scored.append((score, row))
            if not scored:
                return None
            score, best = max(scored, key=lambda item: item[0])
            if score < 0.35:
                return None
            rows = connection.execute(
                """
                SELECT claim, confidence, document_id, locator
                  FROM claims
                 WHERE question_id = ?
                 ORDER BY id
                """,
                (best["id"],),
            ).fetchall()
            try:
                gap_rows = connection.execute(
                    """
                    SELECT deciding_record
                      FROM question_gaps
                     WHERE question_id = ?
                     ORDER BY id
                    """,
                    (best["id"],),
                ).fetchall()
            except sqlite3.OperationalError:
                gap_rows = []

        claims: list[Claim] = []
        for row in rows:
            locator_text = row["locator"] or ""
            page_match = re.search(r"\bpages?\s+([\d,\s]+)", locator_text)
            timestamp_match = re.search(r"\btimestamp\s+(.+)$", locator_text)
            pages = (
                tuple(int(page) for page in re.findall(r"\d+", page_match.group(1)))
                if page_match
                else ()
            )
            locators = (
                tuple(
                    EvidenceLocator(document_id=row["document_id"], page=page)
                    for page in pages
                )
                or (
                    EvidenceLocator(
                        document_id=row["document_id"],
                        timestamp=(
                            timestamp_match.group(1) if timestamp_match else None
                        ),
                    ),
                )
            )
            raw_confidence = (row["confidence"] or "").lower()
            confidence = (
                Confidence.VERIFIED
                if raw_confidence.startswith("verified")
                else Confidence.SUPPORTED_INTERPRETATION
                if raw_confidence.startswith("supported")
                else Confidence.DISPUTED
                if raw_confidence.startswith("disputed")
                else Confidence.UNRESOLVED
            )
            claims.append(
                Claim(
                    text=row["claim"],
                    confidence=confidence,
                    locators=locators,
                    does_not_establish=(
                        "This case-specific finding does not establish facts beyond "
                        "the cited record, locator, version, and proceeding."
                    ),
                )
            )
        return Analysis(
            short_answer=best["short_answer"],
            claims=tuple(claims),
            answer_claim_indices=tuple(range(len(claims))),
            gaps=tuple(
                EvidenceGap(
                    description="The curated answer identifies a missing record.",
                    deciding_record=row["deciding_record"],
                )
                for row in gap_rows
            ),
        )

    def load_yaml(self, filename: str) -> object:
        allowed = {
            "manifest.yaml",
            "acquisition-log.yaml",
            "authority-chain.yaml",
            "water-law.yaml",
            "questions.yaml",
            "records-requests.yaml",
        }
        if filename not in allowed:
            raise ValueError(f"YAML source is not allowlisted: {filename}")
        return yaml.safe_load(
            (self.case_root / filename).read_text(encoding="utf-8")
        )


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    returncode: int
    stdout: str
    stderr: str


class NodeCommandAdapter:
    COMMANDS: dict[str, tuple[str, ...]] = {
        "build_case_db": ("npm", "run", "build:case-db"),
        "build_casebook": ("npm", "run", "build:casebook"),
    }

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def run(self, command_id: str, timeout_seconds: int = 300) -> CommandResult:
        command = self.COMMANDS.get(command_id)
        if command is None:
            raise ValueError(f"Node command is not allowlisted: {command_id}")
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return CommandResult(
            command_id=command_id,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
