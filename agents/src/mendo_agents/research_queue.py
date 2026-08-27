"""Operational research queue created from accepted chatbot evidence gaps."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_question_runs (
                  id TEXT PRIMARY KEY,
                  case_id TEXT NOT NULL,
                  question TEXT NOT NULL,
                  origin_type TEXT NOT NULL,
                  initiating_actor TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_question_run_gaps (
                  run_id TEXT NOT NULL,
                  gap_id TEXT NOT NULL,
                  was_new INTEGER NOT NULL,
                  description TEXT,
                  deciding_record TEXT,
                  likely_custodian TEXT,
                  rationale TEXT,
                  related_claim_indices_json TEXT NOT NULL DEFAULT '[]',
                  PRIMARY KEY (run_id, gap_id),
                  FOREIGN KEY (run_id) REFERENCES research_question_runs(id),
                  FOREIGN KEY (gap_id) REFERENCES research_queue(id)
                );
                CREATE TABLE IF NOT EXISTS research_question_analyses (
                  question_run_id TEXT PRIMARY KEY,
                  schema_version INTEGER NOT NULL,
                  result_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (question_run_id)
                    REFERENCES research_question_runs(id)
                );
                INSERT OR IGNORE INTO research_question_runs
                  (id, case_id, question, origin_type, initiating_actor,
                   created_at)
                SELECT COALESCE(origin_run_id, 'legacy-' || id),
                       case_id, question, origin_type, initiating_actor,
                       created_at
                  FROM research_queue;
                INSERT OR IGNORE INTO research_question_run_gaps
                  (run_id, gap_id, was_new)
                SELECT COALESCE(origin_run_id, 'legacy-' || id), id, 1
                  FROM research_queue;
                """
            )
            gap_columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(research_question_run_gaps)"
                )
            }
            if "rationale" not in gap_columns:
                connection.execute(
                    "ALTER TABLE research_question_run_gaps "
                    "ADD COLUMN rationale TEXT"
                )
            for name in ("description", "deciding_record", "likely_custodian"):
                if name not in gap_columns:
                    connection.execute(
                        f"ALTER TABLE research_question_run_gaps "
                        f"ADD COLUMN {name} TEXT"
                    )
            if "related_claim_indices_json" not in gap_columns:
                connection.execute(
                    "ALTER TABLE research_question_run_gaps "
                    "ADD COLUMN related_claim_indices_json TEXT "
                    "NOT NULL DEFAULT '[]'"
                )

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
        provenance_snapshot: dict[str, object] | None = None,
    ) -> tuple[QueuedResearch, ...]:
        if self._json_mode:
            return self._enqueue_json(
                case_id,
                question,
                gaps,
                origin_type=origin_type,
                origin_run_id=origin_run_id,
                initiating_actor=initiating_actor,
                provenance_snapshot=provenance_snapshot,
            )
        now = datetime.now(UTC).isoformat()
        run_id = origin_run_id or f"enqueue-{uuid4()}"
        snapshot_json = (
            json.dumps(provenance_snapshot, sort_keys=True)
            if provenance_snapshot is not None
            else None
        )
        snapshot_version = (
            int(provenance_snapshot["schema_version"])
            if provenance_snapshot is not None
            else None
        )
        queued: list[QueuedResearch] = []
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_question_runs
                  (id, case_id, question, origin_type, initiating_actor,
                   created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    case_id,
                    question,
                    origin_type,
                    initiating_actor,
                    now,
                ),
            )
            if snapshot_json is not None:
                connection.execute(
                    """
                    INSERT INTO research_question_analyses
                      (question_run_id, schema_version, result_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (run_id, snapshot_version, snapshot_json, now),
                )
            for gap in gaps:
                identity = "\n".join(
                    (
                        case_id.strip().lower(),
                        gap.deciding_record.strip().lower(),
                    )
                )
                item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                was_new = (
                    connection.execute(
                        "SELECT 1 FROM research_queue WHERE id = ?",
                        (item_id,),
                    ).fetchone()
                    is None
                )
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
                connection.execute(
                    """
                    INSERT INTO research_question_run_gaps
                      (run_id, gap_id, was_new, description, deciding_record,
                       likely_custodian, rationale,
                       related_claim_indices_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id, gap_id) DO UPDATE SET
                      description = excluded.description,
                      deciding_record = excluded.deciding_record,
                      likely_custodian = excluded.likely_custodian,
                      rationale = excluded.rationale,
                      related_claim_indices_json =
                        excluded.related_claim_indices_json
                    """,
                    (
                        run_id,
                        item_id,
                        int(was_new),
                        gap.description,
                        gap.deciding_record,
                        gap.likely_custodian,
                        gap.rationale,
                        json.dumps(gap.related_claim_indices),
                    ),
                )
                status = str(
                    connection.execute(
                        "SELECT status FROM research_queue WHERE id = ?",
                        (item_id,),
                    ).fetchone()["status"]
                )
                queued.append(
                    QueuedResearch(
                        id=item_id,
                        deciding_record=gap.deciding_record,
                        status=status,
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
        provenance_snapshot: dict[str, object] | None,
    ) -> tuple[QueuedResearch, ...]:
        now = datetime.now(UTC).isoformat()
        lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._read_json()
            run_id = origin_run_id or f"enqueue-{uuid4()}"
            if provenance_snapshot is not None:
                question_runs = state.setdefault("__question_runs__", {})
                question_runs[run_id] = {
                    "id": run_id,
                    "case_id": case_id,
                    "question": question,
                    "origin_type": origin_type,
                    "initiating_actor": initiating_actor,
                    "created_at": now,
                    "provenance_snapshot": provenance_snapshot,
                    "gaps": [],
                }
            queued: list[QueuedResearch] = []
            for gap in gaps:
                identity = "\n".join(
                    (
                        case_id.strip().lower(),
                        gap.deciding_record.strip().lower(),
                    )
                )
                item_id = hashlib.sha256(
                    identity.encode("utf-8")
                ).hexdigest()[:20]
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
                if provenance_snapshot is not None:
                    question_runs[run_id]["gaps"].append(
                        {
                            "gap_id": item_id,
                            "description": gap.description,
                            "deciding_record": gap.deciding_record,
                            "likely_custodian": gap.likely_custodian,
                            "rationale": gap.rationale,
                            "related_claim_indices": list(
                                gap.related_claim_indices
                            ),
                        }
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
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except (OSError, TypeError) as error:
            raise RuntimeError(
                f"Research queue state cannot be written: {self.path}: {error}"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)
