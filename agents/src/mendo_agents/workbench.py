"""Private browser Workbench for reviewing research leads and staged records."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from .config import Settings
from .acquisition_engineering import (
    AcquisitionEngineeringStore,
    FoundryAcquisitionEngineer,
    ResearchRecoveryOrchestrator,
)
from .repository import CorpusRepository
from .research_queue import ResearchQueue
from .research_dispatch import (
    FoundryWebSearchScout,
    ResearchDirectiveStore,
    ResearchDispatchError,
    ResearchDispatcher,
)


def is_trusted_private_client(address: str) -> bool:
    try:
        client = ipaddress.ip_address(address)
    except ValueError:
        return False
    return client.is_private or client.is_loopback


MAX_DECISION_BYTES = 16_384
MAX_NOTE_CHARACTERS = 2_000
VALID_ACTIONS = {
    "approve_registration": "registration_approved",
    "continue_research": "approved_search",
    "reject": "rejected",
}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class WorkbenchError(RuntimeError):
    """A safe validation error that may be returned to the private client."""


class CandidateStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._cache_key: tuple[tuple[str, int, int], ...] | None = None
        self._cached_candidates: list[dict[str, object]] = []
        self.validation_errors: list[dict[str, str]] = []

    def list_candidates(self) -> list[dict[str, object]]:
        bundle_paths = sorted(self.root.glob("*/review-bundle.json"))
        cache_key = tuple(
            (
                str(path),
                path.stat().st_mtime_ns,
                path.stat().st_size,
            )
            for path in bundle_paths
        )
        if cache_key == self._cache_key:
            return self._cached_candidates
        candidates: list[dict[str, object]] = []
        validation_errors: list[dict[str, str]] = []
        seen: set[str] = set()
        if not self.root.exists():
            return candidates
        for bundle_path in bundle_paths:
            try:
                payload = json.loads(bundle_path.read_text(encoding="utf-8"))
                raw_candidates = payload.get("candidates")
                if not isinstance(raw_candidates, list):
                    raise RuntimeError("candidates must be an array")
                bundle_candidates = []
                for raw in raw_candidates:
                    candidate = self._validate_candidate(bundle_path.parent, raw)
                    candidate_id = str(candidate["id"])
                    if candidate_id in seen:
                        raise RuntimeError(
                            f"duplicate candidate ID: {candidate_id}"
                        )
                    seen.add(candidate_id)
                    bundle_candidates.append(candidate)
                candidates.extend(bundle_candidates)
            except (OSError, json.JSONDecodeError, RuntimeError) as error:
                validation_errors.append(
                    {
                        "bundle": str(bundle_path.relative_to(self.root)),
                        "error": str(error),
                    }
                )
        self._cache_key = cache_key
        self._cached_candidates = candidates
        self.validation_errors = validation_errors
        return self._cached_candidates

    def get_candidate(self, candidate_id: str) -> dict[str, object]:
        for candidate in self.list_candidates():
            if candidate["id"] == candidate_id:
                return candidate
        raise WorkbenchError(f"Unknown candidate: {candidate_id}")

    def snapshot_for(
        self, candidate_id: str, *, preview: bool
    ) -> tuple[object, str, int, str]:
        candidate = self.get_candidate(candidate_id)
        key = "_preview_path" if preview else "_file_path"
        mime_key = "_preview_mime" if preview else "mime_type"
        path = candidate.get(key)
        if not isinstance(path, Path):
            raise WorkbenchError(
                f"Candidate {candidate_id} has no {'preview' if preview else 'file'}"
            )
        content_type = str(candidate.get(mime_key) or "application/octet-stream")
        expected_bytes = (
            candidate.get("preview_bytes") if preview else candidate["bytes"]
        )
        expected_sha256 = (
            candidate.get("preview_sha256") if preview else candidate["sha256"]
        )
        if not isinstance(expected_bytes, int) or not isinstance(
            expected_sha256, str
        ):
            raise RuntimeError(
                f"Candidate snapshot metadata is incomplete: {candidate_id}"
            )
        snapshot = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    snapshot.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if size != expected_bytes:
                raise RuntimeError(
                    f"Candidate snapshot byte count mismatch: {candidate_id}"
                )
            if digest.hexdigest() != expected_sha256:
                raise RuntimeError(
                    f"Candidate snapshot SHA-256 mismatch: {candidate_id}"
                )
            snapshot.seek(0)
            return snapshot, content_type, size, path.name
        except Exception:
            snapshot.close()
            raise

    def _validate_candidate(
        self, bundle_root: Path, raw: object
    ) -> dict[str, object]:
        if not isinstance(raw, dict):
            raise RuntimeError("Every review candidate must be an object")
        required_strings = (
            "id",
            "title",
            "publisher",
            "source_url",
            "retrieved_at",
            "status",
            "mime_type",
            "sha256",
            "file_path",
        )
        for name in required_strings:
            if not isinstance(raw.get(name), str) or not str(raw[name]).strip():
                raise RuntimeError(f"Candidate field {name} must be a string")
        candidate_id = str(raw["id"])
        if not ID_PATTERN.fullmatch(candidate_id):
            raise RuntimeError(f"Invalid candidate ID: {candidate_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(raw["sha256"])):
            raise RuntimeError(f"Invalid candidate SHA-256: {candidate_id}")
        if not isinstance(raw.get("bytes"), int) or int(raw["bytes"]) < 0:
            raise RuntimeError(f"Invalid candidate byte count: {candidate_id}")
        for name in ("establishes", "does_not_establish", "related_lead_ids"):
            value = raw.get(name, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise RuntimeError(f"Candidate field {name} must be a string array")
        proposed_manifest = raw.get("proposed_manifest")
        if not isinstance(proposed_manifest, dict):
            raise RuntimeError(
                f"Candidate proposed_manifest must be an object: {candidate_id}"
            )

        file_path = self._resolve_file(bundle_root, str(raw["file_path"]))
        preview_path: Path | None = None
        preview_mime: str | None = None
        if raw.get("preview_path") is not None:
            if not isinstance(raw["preview_path"], str):
                raise RuntimeError(
                    f"Candidate preview_path must be a string: {candidate_id}"
                )
            preview_path = self._resolve_file(bundle_root, str(raw["preview_path"]))
            preview_mime = mimetypes.guess_type(preview_path.name)[0]
            if preview_mime not in {"image/jpeg", "image/png", "image/webp"}:
                raise RuntimeError(
                    f"Candidate preview type is not allowed: {candidate_id}"
                )
            if not isinstance(raw.get("preview_bytes"), int):
                raise RuntimeError(
                    f"Candidate preview_bytes must be an integer: {candidate_id}"
                )
            if not re.fullmatch(
                r"[0-9a-f]{64}", str(raw.get("preview_sha256", ""))
            ):
                raise RuntimeError(
                    f"Candidate preview_sha256 is invalid: {candidate_id}"
                )

        candidate = dict(raw)
        candidate["_file_path"] = file_path
        candidate["_preview_path"] = preview_path
        candidate["_preview_mime"] = preview_mime
        self._verify_file(candidate, file_path)
        if preview_path is not None:
            self._verify_preview(candidate, preview_path, preview_mime)
        candidate["file_url"] = (
            f"/api/workbench/candidates/{quote(candidate_id)}/file"
        )
        candidate["preview_url"] = (
            f"/api/workbench/candidates/{quote(candidate_id)}/preview"
            if preview_path is not None
            else None
        )
        return candidate

    @staticmethod
    def _verify_file(candidate: dict[str, object], path: Path) -> None:
        candidate_id = str(candidate["id"])
        if path.stat().st_size != candidate["bytes"]:
            raise RuntimeError(f"Candidate byte count mismatch: {candidate_id}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != candidate["sha256"]:
            raise RuntimeError(f"Candidate SHA-256 mismatch: {candidate_id}")
        if candidate["mime_type"] == "application/pdf":
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise RuntimeError(f"Candidate is not a PDF: {candidate_id}")
        if candidate["mime_type"] in {"application/json", "application/geo+json"}:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(
                    f"Candidate is not valid JSON: {candidate_id}"
                ) from error

    @staticmethod
    def _verify_preview(
        candidate: dict[str, object],
        path: Path,
        content_type: str | None,
    ) -> None:
        candidate_id = str(candidate["id"])
        if path.stat().st_size != candidate["preview_bytes"]:
            raise RuntimeError(
                f"Candidate preview byte count mismatch: {candidate_id}"
            )
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != candidate["preview_sha256"]:
            raise RuntimeError(
                f"Candidate preview SHA-256 mismatch: {candidate_id}"
            )
        signatures = {
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/jpeg": b"\xff\xd8\xff",
            "image/webp": b"RIFF",
        }
        expected = signatures.get(content_type)
        with path.open("rb") as stream:
            if expected is None or stream.read(len(expected)) != expected:
                raise RuntimeError(
                    f"Candidate preview content is invalid: {candidate_id}"
                )

    def _resolve_file(self, bundle_root: Path, relative: str) -> Path:
        candidate = (bundle_root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise RuntimeError(
                f"Review bundle file escapes staging root: {relative}"
            ) from error
        if not candidate.is_file():
            raise RuntimeError(f"Review bundle file is unavailable: {candidate}")
        return candidate


class WorkbenchStore:
    def __init__(self, queue_path: Path, candidates: CandidateStore) -> None:
        if queue_path.suffix == ".json":
            raise RuntimeError("Workbench requires the SQLite research queue")
        self.queue_path = queue_path
        self.candidates = candidates
        ResearchQueue(self.queue_path)
        self.directive_store = ResearchDirectiveStore(self.queue_path)
        self.acquisition_store = AcquisitionEngineeringStore(self.queue_path)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workbench_decisions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id TEXT NOT NULL,
                  candidate_sha256 TEXT,
                  action TEXT NOT NULL,
                  note TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(workbench_decisions)"
                )
            }
            if "candidate_sha256" not in columns:
                connection.execute(
                    "ALTER TABLE workbench_decisions "
                    "ADD COLUMN candidate_sha256 TEXT"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workbench_registrations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id TEXT NOT NULL,
                  candidate_sha256 TEXT NOT NULL,
                  source_id TEXT NOT NULL,
                  capture_path TEXT NOT NULL,
                  registered_at TEXT NOT NULL,
                  UNIQUE(candidate_id, candidate_sha256)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.queue_path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.row_factory = sqlite3.Row
        return connection

    def queue(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, case_id, question, description, deciding_record,
                       likely_custodian, status, created_at, last_seen_at,
                       occurrence_count
                  FROM research_queue
                 ORDER BY last_seen_at DESC, id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def research_activity(self) -> list[dict[str, object]]:
        result = []
        for directive in self.directive_store.list():
            public = asdict(directive)
            runs = self.directive_store.runs(directive.id)
            latest = runs[0] if runs else None
            if latest is not None:
                diagnosis = self.acquisition_store.get_for_run(
                    int(latest["id"])
                )
                latest["acquisition_diagnosis"] = (
                    asdict(diagnosis) if diagnosis is not None else None
                )
            if latest is not None and latest.get("report_json"):
                try:
                    latest["report"] = json.loads(str(latest["report_json"]))
                except json.JSONDecodeError as error:
                    raise RuntimeError(
                        f"Dispatch report is corrupt for {directive.id}"
                    ) from error
                del latest["report_json"]
            public["latest_run"] = latest
            result.append(public)
        return result

    def progress_summary(self) -> dict[str, object]:
        with self._connect() as connection:
            queue_statuses = {
                str(row["status"]): int(row["count"])
                for row in connection.execute(
                    """
                    SELECT status, COUNT(*) AS count
                      FROM research_queue
                     GROUP BY status
                    """
                )
            }
            directive_statuses = {
                str(row["status"]): int(row["count"])
                for row in connection.execute(
                    """
                    SELECT status, COUNT(*) AS count
                      FROM research_directives
                     GROUP BY status
                    """
                )
            }
            run_statuses = {
                str(row["status"]): int(row["count"])
                for row in connection.execute(
                    """
                    SELECT status, COUNT(*) AS count
                      FROM research_dispatch_runs
                     GROUP BY status
                    """
                )
            }
            recent_triage_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                      FROM research_queue
                     WHERE status = 'triage'
                        AND julianday(created_at) >= julianday('now', '-6 hours')
                    """
                ).fetchone()[0]
            )
            decision_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM workbench_decisions"
                ).fetchone()[0]
            )
            registration_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM workbench_registrations"
                ).fetchone()[0]
            )
            latest_activity_at = connection.execute(
                """
                SELECT MAX(activity_at)
                  FROM (
                    SELECT MAX(last_seen_at) AS activity_at FROM research_queue
                    UNION ALL
                    SELECT MAX(updated_at) FROM research_directives
                    UNION ALL
                    SELECT MAX(COALESCE(completed_at, started_at))
                      FROM research_dispatch_runs
                    UNION ALL
                    SELECT MAX(created_at) FROM workbench_decisions
                    UNION ALL
                    SELECT MAX(registered_at) FROM workbench_registrations
                  )
                """
            ).fetchone()[0]
            latest_question_row = connection.execute(
                """
                SELECT r.id, r.question, r.created_at AS last_activity_at,
                       COUNT(g.gap_id) AS gap_count,
                       COALESCE(SUM(g.was_new), 0) AS new_gap_count
                  FROM research_question_runs r
                  LEFT JOIN research_question_run_gaps g ON g.run_id = r.id
                 GROUP BY r.id
                 ORDER BY r.created_at DESC, r.id DESC
                 LIMIT 1
                """
            ).fetchone()
            latest_question = None
            if latest_question_row is not None:
                run_id = str(latest_question_row["id"])
                question = str(latest_question_row["question"])
                latest_statuses = {
                    str(row["status"]): int(row["count"])
                    for row in connection.execute(
                        """
                        SELECT q.status, COUNT(*) AS count
                          FROM research_question_run_gaps g
                          JOIN research_queue q ON q.id = g.gap_id
                         WHERE g.run_id = ?
                         GROUP BY q.status
                        """,
                        (run_id,),
                    )
                }
                latest_directive_statuses = {
                    str(row["status"]): int(row["count"])
                    for row in connection.execute(
                        """
                        SELECT d.status, COUNT(DISTINCT d.id) AS count
                          FROM research_directives d
                          JOIN research_directive_question_runs q
                            ON q.directive_id = d.id
                         WHERE q.question_run_id = ?
                         GROUP BY d.status
                        """,
                        (run_id,),
                    )
                }
                gap_count = int(latest_question_row["gap_count"])
                new_gap_count = int(latest_question_row["new_gap_count"])
                latest_question = {
                    "run_id": run_id,
                    "question": question,
                    "last_activity_at": str(
                        latest_question_row["last_activity_at"]
                    ),
                    "gap_count": gap_count,
                    "new_gap_count": new_gap_count,
                    "matched_gap_count": gap_count - new_gap_count,
                    "gap_statuses": latest_statuses,
                    "directive_statuses": latest_directive_statuses,
                }
        return {
            "queue_count": sum(queue_statuses.values()),
            "queue_statuses": queue_statuses,
            "recent_triage_count": recent_triage_count,
            "directive_count": sum(directive_statuses.values()),
            "directive_statuses": directive_statuses,
            "run_count": sum(run_statuses.values()),
            "run_statuses": run_statuses,
            "decision_count": decision_count,
            "registration_count": registration_count,
            "latest_activity_at": latest_activity_at,
            "latest_question": latest_question,
            "triage_automation": {
                "configured": False,
                "state": "not_configured",
            },
        }

    def approve_research_directive(
        self, directive_id: str, actor: str
    ) -> dict[str, object]:
        return asdict(self.directive_store.approve(directive_id, actor=actor))

    def candidates_with_decisions(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            decisions = connection.execute(
                """
                SELECT d.candidate_id, d.candidate_sha256, d.action, d.note,
                       d.actor, d.created_at
                  FROM workbench_decisions d
                  JOIN (
                    SELECT candidate_id, candidate_sha256, MAX(id) AS id
                      FROM workbench_decisions
                     WHERE candidate_sha256 IS NOT NULL
                     GROUP BY candidate_id, candidate_sha256
                  ) latest ON latest.id = d.id
                """
            ).fetchall()
            registrations = connection.execute(
                """
                SELECT candidate_id, candidate_sha256, source_id, capture_path,
                       registered_at
                  FROM workbench_registrations
                """
            ).fetchall()
        latest = {
            (str(row["candidate_id"]), str(row["candidate_sha256"])): dict(row)
            for row in decisions
        }
        registered = {
            (str(row["candidate_id"]), str(row["candidate_sha256"])): dict(row)
            for row in registrations
        }
        result = []
        for candidate in self.candidates.list_candidates():
            public = {
                key: value
                for key, value in candidate.items()
                if not key.startswith("_")
            }
            public["latest_decision"] = latest.get(
                (str(candidate["id"]), str(candidate["sha256"]))
            )
            public["canonical_registration"] = registered.get(
                (str(candidate["id"]), str(candidate["sha256"]))
            )
            result.append(public)
        return result

    def candidate_validation_errors(self) -> list[dict[str, str]]:
        self.candidates.list_candidates()
        return self.candidates.validation_errors

    def candidate_with_decision(self, candidate_id: str) -> dict[str, object]:
        candidate = self.candidates.get_candidate(candidate_id)
        public = {
            key: value for key, value in candidate.items() if not key.startswith("_")
        }
        with self._connect() as connection:
            decision = connection.execute(
                """
                SELECT candidate_sha256, action, note, actor, created_at
                  FROM workbench_decisions
                 WHERE candidate_id = ? AND candidate_sha256 = ?
                 ORDER BY id DESC
                 LIMIT 1
                """,
                (candidate_id, candidate["sha256"]),
            ).fetchone()
            registration = connection.execute(
                """
                SELECT candidate_sha256, source_id, capture_path, registered_at
                  FROM workbench_registrations
                 WHERE candidate_id = ? AND candidate_sha256 = ?
                 LIMIT 1
                """,
                (candidate_id, candidate["sha256"]),
            ).fetchone()
        public["latest_decision"] = dict(decision) if decision else None
        public["canonical_registration"] = (
            dict(registration) if registration else None
        )
        return public

    def record_registration(
        self,
        candidate_id: str,
        candidate_sha256: str,
        source_id: str,
        capture_path: str,
    ) -> dict[str, str]:
        candidate = self.candidates.get_candidate(candidate_id)
        if not hmac.compare_digest(
            str(candidate["sha256"]), candidate_sha256
        ):
            raise WorkbenchError(
                "Candidate bytes changed after approval; registration refused"
            )
        normalized_source_id = source_id.strip()
        normalized_capture_path = capture_path.strip()
        if not normalized_source_id or not normalized_capture_path:
            raise WorkbenchError(
                "Registration requires a source ID and canonical capture path"
            )
        registered_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            decision = connection.execute(
                """
                SELECT action
                  FROM workbench_decisions
                 WHERE candidate_id = ? AND candidate_sha256 = ?
                 ORDER BY id DESC
                 LIMIT 1
                """,
                (candidate_id, candidate_sha256),
            ).fetchone()
            if decision is None or decision["action"] != "approve_registration":
                raise WorkbenchError(
                    "Candidate lacks a current approval for registration"
                )
            connection.execute(
                """
                INSERT INTO workbench_registrations
                  (candidate_id, candidate_sha256, source_id, capture_path,
                   registered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    candidate_sha256,
                    normalized_source_id,
                    normalized_capture_path,
                    registered_at,
                ),
            )
            for lead_id in candidate.get("related_lead_ids", []):
                cursor = connection.execute(
                    "UPDATE research_queue SET status = 'registered' WHERE id = ?",
                    (lead_id,),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Registered candidate refers to missing lead: {lead_id}"
                    )
        return {
            "candidate_id": candidate_id,
            "candidate_sha256": candidate_sha256,
            "source_id": normalized_source_id,
            "capture_path": normalized_capture_path,
            "registered_at": registered_at,
        }

    def decide(
        self,
        candidate_id: str,
        candidate_sha256: str,
        action: str,
        note: str,
        actor: str,
    ) -> dict[str, object]:
        candidate = self.candidates.get_candidate(candidate_id)
        if not hmac.compare_digest(
            str(candidate["sha256"]), candidate_sha256
        ):
            raise WorkbenchError(
                "Candidate bytes changed after review; reload before deciding"
            )
        file_path = candidate.get("_file_path")
        if not isinstance(file_path, Path):
            raise RuntimeError(f"Candidate file is unavailable: {candidate_id}")
        self.candidates._verify_file(candidate, file_path)
        if action not in VALID_ACTIONS:
            raise WorkbenchError(f"Unsupported decision action: {action}")
        normalized_note = " ".join(note.split())
        if len(normalized_note) > MAX_NOTE_CHARACTERS:
            raise WorkbenchError(
                f"Decision note exceeds {MAX_NOTE_CHARACTERS} characters"
            )
        normalized_actor = " ".join(actor.split())[:200] or "cio"
        created_at = datetime.now(UTC).isoformat()
        related_leads = candidate.get("related_lead_ids", [])
        unmatched_lead_ids: list[str] = []
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workbench_decisions
                  (candidate_id, candidate_sha256, action, note, actor, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    candidate_sha256,
                    action,
                    normalized_note,
                    normalized_actor,
                    created_at,
                ),
            )
            for lead_id in related_leads:
                cursor = connection.execute(
                    "UPDATE research_queue SET status = ? WHERE id = ?",
                    (VALID_ACTIONS[action], lead_id),
                )
                if cursor.rowcount != 1:
                    unmatched_lead_ids.append(str(lead_id))
        return {
            "candidate_id": candidate_id,
            "candidate_sha256": candidate_sha256,
            "action": action,
            "note": normalized_note,
            "actor": normalized_actor,
            "created_at": created_at,
            "canonical_registration_performed": False,
            "unmatched_lead_ids": unmatched_lead_ids,
        }


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    server_version = "MendoWorkbench/0.1"

    @property
    def workbench_server(self) -> "WorkbenchHTTPServer":
        return self.server  # type: ignore[return-value]

    def _authorized(self) -> bool:
        expected = self.workbench_server.proxy_token
        if not expected and self.workbench_server.allow_unauthenticated_loopback:
            return self.client_address[0] in {"127.0.0.1", "::1"}
        if (
            not expected
            and self.workbench_server.allow_unauthenticated_private_network
        ):
            return is_trusted_private_client(self.client_address[0])
        actual = self.headers.get("X-Mendo-Workbench-Auth", "")
        return hmac.compare_digest(expected, actual)

    def _headers(
        self,
        status: HTTPStatus,
        content_type: str,
        *,
        content_disposition: str | None = None,
        content_length: int | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data: "
            "https://tile.openstreetmap.org; object-src 'self'; "
            "frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'",
        )
        if content_disposition:
            self.send_header("Content-Disposition", content_disposition)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.end_headers()

    def _json(self, status: HTTPStatus, value: object) -> None:
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(value, sort_keys=True).encode("utf-8"))

    def _require_authorized(self) -> bool:
        if self._authorized():
            return True
        self._json(HTTPStatus.FORBIDDEN, {"error": "Workbench access denied."})
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._require_authorized():
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/workbench/health":
                self._json(HTTPStatus.OK, {"status": "ok"})
                return
            if path == "/api/workbench/queue":
                items = self.workbench_server.store.queue()
                self._json(HTTPStatus.OK, {"items": items, "count": len(items)})
                return
            if path == "/api/workbench/research-activity":
                items = self.workbench_server.store.research_activity()
                self._json(HTTPStatus.OK, {"items": items, "count": len(items)})
                return
            if path == "/api/workbench/progress":
                self._json(
                    HTTPStatus.OK,
                    self.workbench_server.store.progress_summary(),
                )
                return
            if path == "/api/workbench/candidates":
                items = self.workbench_server.store.candidates_with_decisions()
                self._json(
                    HTTPStatus.OK,
                    {
                        "items": items,
                        "count": len(items),
                        "validation_errors": (
                            self.workbench_server.store.candidate_validation_errors()
                        ),
                    },
                )
                return
            match = re.fullmatch(
                r"/api/workbench/candidates/([^/]+)(?:/(file|preview))?", path
            )
            if match:
                candidate_id = unquote(match.group(1))
                asset = match.group(2)
                if asset:
                    self._serve_candidate_file(
                        candidate_id, preview=asset == "preview"
                    )
                else:
                    self._json(
                        HTTPStatus.OK,
                        self.workbench_server.store.candidate_with_decision(
                            candidate_id
                        ),
                    )
                return
            self._serve_static(path)
        except WorkbenchError as error:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(error)})
        except Exception as error:
            self.log_error("Workbench request failed: %s", type(error).__name__)
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Workbench could not load the requested evidence."},
            )

    def do_POST(self) -> None:  # noqa: N802
        if not self._require_authorized():
            return
        path = urlsplit(self.path).path
        directive_match = re.fullmatch(
            r"/api/workbench/research-directives/([^/]+)/approval", path
        )
        if directive_match:
            try:
                actor = self.headers.get("X-Mendo-Workbench-User", "cio")
                result = self.workbench_server.store.approve_research_directive(
                    unquote(directive_match.group(1)), actor
                )
                self._json(HTTPStatus.OK, result)
            except (ResearchDispatchError, ValueError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        dispatch_match = re.fullmatch(
            r"/api/workbench/research-directives/([^/]+)/dispatch", path
        )
        if dispatch_match:
            dispatcher = self.workbench_server.research_dispatcher
            if dispatcher is None:
                self._json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error": (
                            "Foundry dispatch is not configured for this "
                            "Workbench process."
                        )
                    },
                )
                return
            try:
                result = dispatcher.dispatch(unquote(dispatch_match.group(1)))
                self._json(HTTPStatus.OK, result)
            except ResearchDispatchError as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        if path != "/api/workbench/decisions":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"error": "Content-Type must be application/json."},
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request length."})
            return
        if length <= 0 or length > MAX_DECISION_BYTES:
            self._json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "Request body is empty or too large."},
            )
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise WorkbenchError("Decision body must be an object")
            candidate_id = payload.get("candidate_id")
            candidate_sha256 = payload.get("candidate_sha256")
            action = payload.get("action")
            note = payload.get("note", "")
            if not all(
                isinstance(value, str)
                for value in (
                    candidate_id,
                    candidate_sha256,
                    action,
                    note,
                )
            ):
                raise WorkbenchError(
                    "Decision requires string candidate_id, candidate_sha256, "
                    "action, and note"
                )
            actor = self.headers.get("X-Mendo-Workbench-User", "cio")
            result = self.workbench_server.store.decide(
                candidate_id,
                candidate_sha256,
                action,
                note,
                actor,
            )
            self._json(HTTPStatus.OK, result)
        except (json.JSONDecodeError, WorkbenchError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            self.log_error("Workbench decision failed: %s", type(error).__name__)
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Decision was not recorded."},
            )

    def _serve_candidate_file(self, candidate_id: str, *, preview: bool) -> None:
        snapshot, content_type, size, filename = (
            self.workbench_server.store.candidates.snapshot_for(
            candidate_id, preview=preview
            )
        )
        disposition = "inline" if preview or content_type == "application/pdf" else "attachment"
        safe_filename = filename.replace('"', "_")
        try:
            self._headers(
                HTTPStatus.OK,
                content_type,
                content_disposition=f'{disposition}; filename="{safe_filename}"',
                content_length=size,
            )
            shutil.copyfileobj(snapshot, self.wfile)
        finally:
            snapshot.close()

    def _serve_static(self, request_path: str) -> None:
        relative = request_path.lstrip("/") or "workbench.html"
        if relative == "workbench":
            relative = "workbench.html"
        candidate = (self.workbench_server.web_root / relative).resolve()
        try:
            candidate.relative_to(self.workbench_server.web_root)
        except ValueError:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Forbidden."})
            return
        if not candidate.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        content_type = mimetypes.guess_type(candidate.name)[0]
        self._headers(
            HTTPStatus.OK,
            f"{content_type or 'application/octet-stream'}"
            + (
                "; charset=utf-8"
                if content_type and content_type.startswith("text/")
                else ""
            ),
        )
        self.wfile.write(candidate.read_bytes())


class WorkbenchHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        store: WorkbenchStore,
        web_root: Path,
        proxy_token: str | None,
        research_dispatcher: ResearchDispatcher | None = None,
        allow_unauthenticated_loopback: bool = False,
        allow_unauthenticated_private_network: bool = False,
    ) -> None:
        self.store = store
        self.web_root = web_root.resolve()
        self.proxy_token = proxy_token or ""
        self.research_dispatcher = research_dispatcher
        self.allow_unauthenticated_loopback = allow_unauthenticated_loopback
        self.allow_unauthenticated_private_network = (
            allow_unauthenticated_private_network
        )
        super().__init__(address, WorkbenchRequestHandler)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-workbench")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4180)
    parser.add_argument(
        "--allow-unauthenticated-loopback",
        action="store_true",
        help="allow direct loopback access for local development only",
    )
    parser.add_argument(
        "--allow-unauthenticated-private-network",
        action="store_true",
        help="trust direct clients with private or loopback source addresses",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = Settings.from_env(args.repo_root)
    proxy_token = os.environ.get("MENDO_WORKBENCH_PROXY_TOKEN", "").strip()
    if not proxy_token and not (
        args.allow_unauthenticated_loopback
        or args.allow_unauthenticated_private_network
    ):
        raise RuntimeError(
            "MENDO_WORKBENCH_PROXY_TOKEN is required unless explicit "
            "unauthenticated local-network access is enabled"
        )
    store = WorkbenchStore(
        settings.research_queue_path,
        CandidateStore(settings.research_staging_root),
    )
    research_dispatcher = None
    if os.environ.get("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        research_dispatcher = ResearchDispatcher(
            store.directive_store,
            FoundryWebSearchScout(),
            CorpusRepository(settings.repo_root, settings.case_id),
            settings.research_staging_root,
            failure_recovery=ResearchRecoveryOrchestrator(
                AcquisitionEngineeringStore(settings.research_queue_path),
                FoundryAcquisitionEngineer(),
            ),
        )
    server = WorkbenchHTTPServer(
        (args.host, args.port),
        store,
        settings.repo_root / "web",
        proxy_token=proxy_token,
        research_dispatcher=research_dispatcher,
        allow_unauthenticated_loopback=args.allow_unauthenticated_loopback,
        allow_unauthenticated_private_network=(
            args.allow_unauthenticated_private_network
        ),
    )
    print(
        f"Mendocino evidence Workbench: http://{args.host}:{args.port}/workbench",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
