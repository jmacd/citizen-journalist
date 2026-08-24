"""Operational research queue created from accepted chatbot evidence gaps."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import EvidenceGap


@dataclass(frozen=True)
class QueuedResearch:
    id: str
    deciding_record: str
    status: str


class ResearchQueue:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._json_mode = path.suffix == ".json"
        if self._json_mode:
            if self.path.exists():
                self._read_json()
            else:
                self._write_json({})
            return
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_queue (
                  id TEXT PRIMARY KEY,
                  case_id TEXT NOT NULL,
                  question TEXT NOT NULL,
                  description TEXT NOT NULL,
                  deciding_record TEXT NOT NULL,
                  likely_custodian TEXT,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  last_seen_at TEXT NOT NULL,
                  occurrence_count INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(research_queue)")
            }
            migrations = {
                "origin_type": (
                    "ALTER TABLE research_queue ADD COLUMN origin_type TEXT "
                    "NOT NULL DEFAULT 'legacy_unknown'"
                ),
                "origin_run_id": (
                    "ALTER TABLE research_queue ADD COLUMN origin_run_id TEXT"
                ),
                "initiating_actor": (
                    "ALTER TABLE research_queue ADD COLUMN initiating_actor TEXT "
                    "NOT NULL DEFAULT 'unknown'"
                ),
            }
            for name, statement in migrations.items():
                if name not in columns:
                    connection.execute(statement)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.row_factory = sqlite3.Row
        return connection

    def enqueue(
        self,
        case_id: str,
        question: str,
        gaps: tuple[EvidenceGap, ...],
        *,
        origin_type: str = "agent_analysis",
        origin_run_id: str | None = None,
        initiating_actor: str = "unknown",
    ) -> tuple[QueuedResearch, ...]:
        if self._json_mode:
            return self._enqueue_json(
                case_id,
                question,
                gaps,
                origin_type=origin_type,
                origin_run_id=origin_run_id,
                initiating_actor=initiating_actor,
            )
        now = datetime.now(UTC).isoformat()
        queued: list[QueuedResearch] = []
        with self._connect() as connection:
            for gap in gaps:
                identity = "\n".join(
                    (
                        case_id.strip().lower(),
                        gap.deciding_record.strip().lower(),
                    )
                )
                item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                connection.execute(
                    """
                    INSERT INTO research_queue
                      (id, case_id, question, description, deciding_record,
                       likely_custodian, status, created_at, last_seen_at,
                       origin_type, origin_run_id, initiating_actor)
                    VALUES (?, ?, ?, ?, ?, ?, 'triage', ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      last_seen_at = excluded.last_seen_at,
                      occurrence_count = occurrence_count + 1
                    """,
                    (
                        item_id,
                        case_id,
                        question,
                        gap.description,
                        gap.deciding_record,
                        gap.likely_custodian,
                        now,
                        now,
                        origin_type,
                        origin_run_id,
                        initiating_actor,
                    ),
                )
                queued.append(
                    QueuedResearch(
                        id=item_id,
                        deciding_record=gap.deciding_record,
                        status="triage",
                    )
                )
        return tuple(queued)

    def _enqueue_json(
        self,
        case_id: str,
        question: str,
        gaps: tuple[EvidenceGap, ...],
        *,
        origin_type: str,
        origin_run_id: str | None,
        initiating_actor: str,
    ) -> tuple[QueuedResearch, ...]:
        now = datetime.now(UTC).isoformat()
        state = self._read_json()
        queued: list[QueuedResearch] = []
        for gap in gaps:
            identity = "\n".join(
                (
                    case_id.strip().lower(),
                    gap.deciding_record.strip().lower(),
                )
            )
            item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
            existing = state.get(item_id)
            if existing is None:
                state[item_id] = {
                    "id": item_id,
                    "case_id": case_id,
                    "question": question,
                    "description": gap.description,
                    "deciding_record": gap.deciding_record,
                    "likely_custodian": gap.likely_custodian,
                    "status": "triage",
                    "created_at": now,
                    "last_seen_at": now,
                    "occurrence_count": 1,
                    "origin_type": origin_type,
                    "origin_run_id": origin_run_id,
                    "initiating_actor": initiating_actor,
                }
            else:
                existing["last_seen_at"] = now
                existing["occurrence_count"] = int(
                    existing["occurrence_count"]
                ) + 1
            queued.append(
                QueuedResearch(
                    id=item_id,
                    deciding_record=gap.deciding_record,
                    status="triage",
                )
            )
        self._write_json(state)
        return tuple(queued)

    def _read_json(self) -> dict[str, dict[str, object]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Research queue state cannot be read: {self.path}: {error}"
            ) from error
        if not isinstance(value, dict):
            raise RuntimeError(
                f"Research queue state must be a JSON object: {self.path}"
            )
        return value

    def _write_json(self, value: dict[str, dict[str, object]]) -> None:
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError as error:
            raise RuntimeError(
                f"Research queue state cannot be written: {self.path}: {error}"
            ) from error
