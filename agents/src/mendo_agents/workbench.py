"""Private browser Workbench for reviewing research leads and staged records."""

from __future__ import annotations

import argparse
import asyncio
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
from .models import ConsultationKind
from .providers import create_reasoner
from .theorem_builder import TheoremBuilderError, build_theorem
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
        seen: dict[str, dict[str, object]] = {}
        if not self.root.exists():
            return candidates
        for bundle_path in bundle_paths:
            try:
                payload = json.loads(bundle_path.read_text(encoding="utf-8"))
                raw_candidates = payload.get("candidates")
                if not isinstance(raw_candidates, list):
                    raise RuntimeError("candidates must be an array")
                bundle_candidates = [
                    self._validate_candidate(bundle_path.parent, raw)
                    for raw in raw_candidates
                ]
                relative_bundle = str(bundle_path.relative_to(self.root))
                for candidate in bundle_candidates:
                    candidate["_bundle_path"] = relative_bundle
                local_seen: dict[str, dict[str, object]] = {}
                for candidate in bundle_candidates:
                    candidate_id = str(candidate["id"])
                    if candidate_id in local_seen:
                        raise RuntimeError(
                            f"duplicate candidate ID within bundle: {candidate_id}"
                        )
                    existing = seen.get(candidate_id)
                    if existing is not None:
                        self._assert_same_candidate(existing, candidate)
                    local_seen[candidate_id] = candidate
                for candidate in bundle_candidates:
                    candidate_id = str(candidate["id"])
                    existing = seen.get(candidate_id)
                    if existing is None:
                        candidate["occurrences"] = [
                            self._candidate_occurrence(candidate)
                        ]
                        candidate["duplicate_occurrence_count"] = 1
                        seen[candidate_id] = candidate
                        candidates.append(candidate)
                    else:
                        self._merge_candidate_occurrence(existing, candidate)
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

    @staticmethod
    def _assert_same_candidate(
        existing: dict[str, object],
        candidate: dict[str, object],
    ) -> None:
        candidate_id = str(candidate["id"])
        identity = (
            "sha256",
            "bytes",
            "mime_type",
        )
        conflicts = [
            name for name in identity if existing.get(name) != candidate.get(name)
        ]
        if CandidateStore._normalized_source_url(
            str(existing["source_url"])
        ) != CandidateStore._normalized_source_url(str(candidate["source_url"])):
            conflicts.append("source_url")
        if conflicts:
            existing_bundle = existing.get("_bundle_path", "unknown bundle")
            candidate_bundle = candidate.get("_bundle_path", "unknown bundle")
            raise RuntimeError(
                f"conflicting duplicate candidate ID: {candidate_id} "
                f"between {existing_bundle} and {candidate_bundle} "
                f"({', '.join(conflicts)})"
            )

    @staticmethod
    def _normalized_source_url(source_url: str) -> str:
        parsed = urlsplit(source_url)
        hostname = parsed.hostname
        if hostname is None:
            return source_url
        try:
            port = parsed.port
        except ValueError:
            return source_url
        default_port = (
            parsed.scheme.lower() == "https" and port == 443
        ) or (parsed.scheme.lower() == "http" and port == 80)
        netloc = hostname.lower()
        if ":" in netloc:
            netloc = f"[{netloc}]"
        if port is not None and not default_port:
            netloc = f"{netloc}:{port}"
        if parsed.username is not None:
            credentials = parsed.username
            if parsed.password is not None:
                credentials = f"{credentials}:{parsed.password}"
            netloc = f"{credentials}@{netloc}"
        return parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=netloc,
            fragment="",
        ).geturl()

    @staticmethod
    def _candidate_occurrence(
        candidate: dict[str, object],
    ) -> dict[str, object]:
        return {
            "bundle": candidate.get("_bundle_path"),
            "title": candidate["title"],
            "publisher": candidate["publisher"],
            "document_date": candidate.get("document_date"),
            "source_url": candidate["source_url"],
            "retrieved_at": candidate["retrieved_at"],
            "version": candidate.get("version"),
            "signature_status": candidate.get("signature_status"),
            "related_lead_ids": list(candidate.get("related_lead_ids", [])),
            "establishes": list(candidate.get("establishes", [])),
            "does_not_establish": list(
                candidate.get("does_not_establish", [])
            ),
            "proposed_manifest": candidate["proposed_manifest"],
        }

    @staticmethod
    def _merge_candidate_occurrence(
        existing: dict[str, object],
        candidate: dict[str, object],
    ) -> None:
        CandidateStore._assert_same_candidate(existing, candidate)
        for name in ("related_lead_ids", "establishes", "does_not_establish"):
            existing_values = list(existing.get(name, []))
            candidate_values = list(candidate.get(name, []))
            existing[name] = list(dict.fromkeys(existing_values + candidate_values))
        occurrences = list(existing.get("occurrences", []))
        occurrences.append(CandidateStore._candidate_occurrence(candidate))
        existing["occurrences"] = occurrences
        existing["duplicate_occurrence_count"] = (
            int(existing.get("duplicate_occurrence_count", 1)) + 1
        )

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
        self.directive_store.recover_interrupted_dispatches()
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cio_consultations (
                  id TEXT PRIMARY KEY,
                  case_id TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  brief TEXT NOT NULL,
                  requested_by TEXT NOT NULL,
                  status TEXT NOT NULL,
                  markdown TEXT NOT NULL DEFAULT '',
                  html TEXT NOT NULL DEFAULT '',
                  analyst_context TEXT NOT NULL DEFAULT '',
                  journalist_context TEXT NOT NULL DEFAULT '',
                  architect_context TEXT NOT NULL DEFAULT '',
                  proposal_json TEXT NOT NULL DEFAULT '',
                  raw_output TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(cio_consultations)")
            }
            for column in (
                "markdown",
                "html",
                "analyst_context",
                "journalist_context",
                "architect_context",
                "proposal_json",
                "raw_output",
            ):
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE cio_consultations ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
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

    def consultations(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, case_id, kind, brief, requested_by, status, markdown, html,
                       analyst_context, journalist_context, architect_context,
                       proposal_json, created_at
                  FROM cio_consultations
                 ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_consultation(
        self,
        case_id: str,
        kind: str,
        brief: str,
        requested_by: str,
        *,
        markdown: str = "",
        html: str = "",
        analyst_context: str = "",
        journalist_context: str = "",
        architect_context: str = "",
    ) -> dict[str, object]:
        allowed = {
            "theorem_proposal",
            "story_update",
            "information_architecture",
            "site_design",
        }
        if kind not in allowed:
            raise WorkbenchError("Unknown consultation type")
        normalized_brief = " ".join(brief.split())
        if not normalized_brief:
            raise WorkbenchError("Consultation brief is required")
        if len(normalized_brief) > MAX_NOTE_CHARACTERS:
            raise WorkbenchError("Consultation brief is too long")
        fields = {
            "markdown": markdown,
            "html": html,
            "analyst_context": analyst_context,
            "journalist_context": journalist_context,
            "architect_context": architect_context,
        }
        if any(not isinstance(value, str) for value in fields.values()):
            raise WorkbenchError("Consultation content must be strings")
        if any(len(value) > MAX_NOTE_CHARACTERS * 4 for value in fields.values()):
            raise WorkbenchError("Consultation content is too long")
        created_at = datetime.now(UTC).isoformat()
        consultation_id = hashlib.sha256(
            f"{case_id}\n{kind}\n{normalized_brief}\n{created_at}".encode()
        ).hexdigest()[:20]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cio_consultations
                  (id, case_id, kind, brief, requested_by, status, markdown, html,
                   analyst_context, journalist_context, architect_context, created_at)
                VALUES (?, ?, ?, ?, ?, 'requested', ?, ?, ?, ?, ?, ?)
                """,
                (
                    consultation_id, case_id, kind, normalized_brief, requested_by,
                    markdown, html, analyst_context, journalist_context,
                    architect_context, created_at,
                ),
            )
        return {
            "id": consultation_id,
            "case_id": case_id,
            "kind": kind,
            "brief": normalized_brief,
            "requested_by": requested_by,
            "status": "requested",
            **fields,
            "created_at": created_at,
        }

    def build_theorem(self, consultation_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM cio_consultations WHERE id = ?", (consultation_id,)
            ).fetchone()
        if row is None:
            raise WorkbenchError("Unknown consultation")
        if row["kind"] != ConsultationKind.THEOREM_PROPOSAL.value:
            raise WorkbenchError("Only theorem consultations can be built here")
        context = self.provenance_questions()
        try:
            proposal, raw = asyncio.run(
                build_theorem(
                    create_reasoner(os.environ.get("MENDO_MODEL_PROVIDER", "scripted")),
                    brief=str(row["brief"]),
                    context=context[:20],
                )
            )
        except (TheoremBuilderError, RuntimeError) as error:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE cio_consultations SET status = 'blocked' WHERE id = ?",
                    (consultation_id,),
                )
            raise WorkbenchError(str(error)) from error
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE cio_consultations
                   SET status = 'proposal_ready', proposal_json = ?, raw_output = ?
                 WHERE id = ?
                """,
                (json.dumps(proposal, ensure_ascii=True), raw, consultation_id),
            )
        result = dict(row)
        result.update(status="proposal_ready", proposal=proposal)
        return result

    def provenance_questions(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.id, r.case_id, r.question, r.origin_type,
                       r.initiating_actor, r.created_at,
                       a.result_json,
                       COUNT(DISTINCT g.gap_id) AS gap_count,
                       COUNT(DISTINCT q.directive_id) AS directive_count
                  FROM research_question_runs r
                  LEFT JOIN research_question_analyses a
                    ON a.question_run_id = r.id
                  LEFT JOIN research_question_run_gaps g
                    ON g.run_id = r.id
                  LEFT JOIN research_directive_question_runs q
                    ON q.question_run_id = r.id
                 GROUP BY r.id
                 ORDER BY r.created_at DESC, r.id DESC
                 LIMIT 100
                """
            ).fetchall()
        result = []
        for row in rows:
            item = {
                key: row[key]
                for key in (
                    "id",
                    "case_id",
                    "question",
                    "origin_type",
                    "initiating_actor",
                    "created_at",
                    "gap_count",
                    "directive_count",
                )
            }
            item["analysis_available"] = row["result_json"] is not None
            if row["result_json"] is not None:
                try:
                    snapshot = json.loads(str(row["result_json"]))
                except json.JSONDecodeError as error:
                    raise RuntimeError(
                        f"Question analysis is corrupt for {row['id']}"
                    ) from error
                item["disposition"] = snapshot.get("disposition")
                analysis = snapshot.get("analysis")
                item["claim_count"] = (
                    len(analysis.get("claims", []))
                    if isinstance(analysis, dict)
                    else 0
                )
                item["conclusion_kind"] = (
                    analysis.get("conclusion_kind")
                    if isinstance(analysis, dict)
                    else None
                )
            else:
                item["disposition"] = None
                item["claim_count"] = 0
                item["conclusion_kind"] = None
            result.append(item)
        return result

    def provenance_graph(self, question_run_id: str) -> dict[str, object]:
        with self._connect() as connection:
            question = connection.execute(
                """
                SELECT r.id, r.case_id, r.question, r.origin_type,
                       r.initiating_actor, r.created_at, a.result_json
                  FROM research_question_runs r
                  LEFT JOIN research_question_analyses a
                    ON a.question_run_id = r.id
                 WHERE r.id = ?
                """,
                (question_run_id,),
            ).fetchone()
            if question is None:
                raise WorkbenchError(
                    f"Unknown question run: {question_run_id}"
                )
            gaps = connection.execute(
                """
                SELECT q.id,
                       COALESCE(g.description, q.description) AS description,
                       COALESCE(g.deciding_record, q.deciding_record)
                         AS deciding_record,
                       COALESCE(g.likely_custodian, q.likely_custodian)
                         AS likely_custodian,
                       q.status, q.created_at,
                       g.was_new, g.rationale,
                       g.related_claim_indices_json
                  FROM research_question_run_gaps g
                  JOIN research_queue q ON q.id = g.gap_id
                 WHERE g.run_id = ?
                 ORDER BY q.created_at, q.id
                """,
                (question_run_id,),
            ).fetchall()
            triage_table = connection.execute(
                """
                SELECT 1
                  FROM sqlite_master
                 WHERE type = 'table' AND name = 'research_triage_runs'
                """
            ).fetchone()
            triage_columns = (
                {
                    str(row["name"])
                    for row in connection.execute(
                        "PRAGMA table_info(research_triage_runs)"
                    )
                }
                if triage_table is not None
                else set()
            )
            directive_column = (
                "directive_id"
                if "directive_id" in triage_columns
                else "NULL AS directive_id"
            )
            triage_runs = (
                connection.execute(
                    f"""
                    SELECT id, status, provider, model, started_at, completed_at,
                           output_json, error_type, error, {directive_column}
                      FROM research_triage_runs
                     WHERE question_run_id = ?
                     ORDER BY id
                    """,
                    (question_run_id,),
                ).fetchall()
                if triage_table is not None
                else []
            )
            directives = connection.execute(
                """
                SELECT DISTINCT d.id, d.title, d.search_brief, d.status,
                       d.created_at, d.updated_at, d.approved_by, d.approved_at,
                       q.attribution
                  FROM research_directives d
                  JOIN research_directive_question_runs q
                    ON q.directive_id = d.id
                 WHERE q.question_run_id = ?
                 ORDER BY d.created_at, d.id
                """,
                (question_run_id,),
            ).fetchall()
            directive_leads = connection.execute(
                """
                SELECT l.directive_id, l.lead_id
                  FROM research_directive_leads l
                  JOIN research_directive_question_runs q
                    ON q.directive_id = l.directive_id
                 WHERE q.question_run_id = ?
                """,
                (question_run_id,),
            ).fetchall()
            dispatch_runs = connection.execute(
                """
                SELECT r.id, r.directive_id, r.status, r.provider, r.model,
                       r.started_at, r.completed_at, r.error_type, r.error,
                       r.cache_status
                  FROM research_dispatch_runs r
                  JOIN research_directive_question_runs q
                    ON q.directive_id = r.directive_id
                 WHERE q.question_run_id = ?
                 ORDER BY r.id
                """,
                (question_run_id,),
            ).fetchall()

        snapshot = None
        if question["result_json"] is not None:
            try:
                snapshot = json.loads(str(question["result_json"]))
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Question analysis is corrupt for {question_run_id}"
                ) from error

        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        node_ids: set[str] = set()
        edge_ids: set[tuple[str, str, str, str]] = set()

        def add_node(
            node_id: str,
            kind: str,
            label: str,
            **attributes: object,
        ) -> None:
            if node_id in node_ids:
                return
            node_ids.add(node_id)
            nodes.append(
                {"id": node_id, "kind": kind, "label": label, **attributes}
            )

        def add_edge(
            source: str,
            target: str,
            kind: str,
            label: str,
            **attributes: object,
        ) -> None:
            identity = (
                source,
                target,
                kind,
                json.dumps(attributes, sort_keys=True),
            )
            if identity in edge_ids:
                return
            edge_ids.add(identity)
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "kind": kind,
                    "label": label,
                    **attributes,
                }
            )

        snapshot_analysis = (
            snapshot.get("analysis")
            if isinstance(snapshot, dict)
            and isinstance(snapshot.get("analysis"), dict)
            else None
        )
        question_node = f"question:{question_run_id}"
        add_node(
            question_node,
            "question",
            str(question["question"]),
            timestamp=question["created_at"],
            status=(
                snapshot.get("disposition")
                if isinstance(snapshot, dict)
                else "legacy"
            ),
            conclusion_kind=(
                snapshot_analysis.get("conclusion_kind")
                if snapshot_analysis is not None
                else None
            ),
            detail=(
                snapshot_analysis.get("scope_statement")
                if snapshot_analysis is not None
                else None
            ),
        )

        analysis = snapshot_analysis
        claims = (
            analysis.get("claims", [])
            if isinstance(analysis, dict)
            else []
        )
        answer_claim_indices = set(
            analysis.get("answer_claim_indices", [])
            if isinstance(analysis, dict)
            else []
        )
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                raise RuntimeError(
                    f"Question claim is corrupt for {question_run_id}"
                )
            claim_node = f"claim:{question_run_id}:{index}"
            add_node(
                claim_node,
                "claim",
                str(claim.get("text", "")),
                status=claim.get("confidence"),
                limitation=claim.get("does_not_establish"),
                answers_question=index in answer_claim_indices,
            )
            add_edge(
                question_node,
                claim_node,
                "answered_by" if index in answer_claim_indices else "analyzed_by",
                "answer relies on" if index in answer_claim_indices else "analysis",
            )
            for citation in claim.get("citations", []):
                if not isinstance(citation, dict):
                    raise RuntimeError(
                        f"Question citation is corrupt for {question_run_id}"
                    )
                document_id = str(citation.get("document_id", "unknown"))
                source_node = f"source:{document_id}"
                add_node(
                    source_node,
                    "source",
                    str(citation.get("title") or document_id),
                    status="invalid" if citation.get("invalid") else "registered",
                    document_id=document_id,
                    publisher=citation.get("publisher"),
                    url=citation.get("url"),
                )
                locator = {
                    key: citation.get(key)
                    for key in ("page", "section", "timestamp", "field")
                    if citation.get(key) is not None
                }
                add_edge(
                    claim_node,
                    source_node,
                    "supported_by",
                    "cites",
                    locator=locator,
                )

        review = (
            snapshot.get("review")
            if isinstance(snapshot, dict)
            else None
        )
        if isinstance(review, dict):
            for index, finding in enumerate(review.get("findings", [])):
                if not isinstance(finding, dict):
                    raise RuntimeError(
                        f"Skeptic finding is corrupt for {question_run_id}"
                    )
                finding_node = f"finding:{question_run_id}:{index}"
                add_node(
                    finding_node,
                    "finding",
                    str(finding.get("message", "")),
                    status=finding.get("severity"),
                    code=finding.get("code"),
                )
                claim_index = finding.get("claim_index")
                if isinstance(claim_index, int) and 0 <= claim_index < len(claims):
                    add_edge(
                        f"claim:{question_run_id}:{claim_index}",
                        finding_node,
                        "reviewed_by",
                        "Skeptic finding",
                    )
                else:
                    add_edge(
                        question_node,
                        finding_node,
                        "reviewed_by",
                        "Skeptic finding",
                    )

        gap_ids = {str(row["id"]) for row in gaps}
        for gap in gaps:
            gap_id = str(gap["id"])
            gap_node = f"gap:{gap_id}"
            add_node(
                gap_node,
                "gap",
                str(gap["deciding_record"]),
                detail=gap["description"],
                custodian=gap["likely_custodian"],
                status=gap["status"],
                was_new=bool(gap["was_new"]),
                timestamp=gap["created_at"],
            )
            try:
                related_claim_indices = json.loads(
                    str(gap["related_claim_indices_json"])
                )
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Gap claim relationships are corrupt for {gap_id}"
                ) from error
            if not isinstance(related_claim_indices, list) or not all(
                isinstance(index, int) for index in related_claim_indices
            ):
                raise RuntimeError(
                    f"Gap claim relationships are invalid for {gap_id}"
                )
            if related_claim_indices:
                for claim_index in related_claim_indices:
                    if 0 <= claim_index < len(claims):
                        add_edge(
                            f"claim:{question_run_id}:{claim_index}",
                            gap_node,
                            "requires_record",
                            "does not establish; needs",
                            rationale=gap["rationale"],
                        )
                    else:
                        raise RuntimeError(
                            f"Gap {gap_id} refers to missing claim "
                            f"{claim_index}"
                        )
            else:
                add_edge(
                    question_node,
                    gap_node,
                    "identified_gap",
                    "identified evidence gap",
                    rationale=gap["rationale"],
                )

        directive_by_id = {str(row["id"]): row for row in directives}
        for row in triage_runs:
            triage_node = f"triage:{row['id']}"
            add_node(
                triage_node,
                "triage",
                f"Foundry triage run {row['id']}",
                status=row["status"],
                provider=row["provider"],
                model=row["model"],
                timestamp=row["started_at"],
                completed_at=row["completed_at"],
                error_type=row["error_type"],
                error=row["error"],
            )
            add_edge(question_node, triage_node, "triaged_by", "triaged by")
            if (
                row["directive_id"] is not None
                and str(row["directive_id"]) in directive_by_id
            ):
                add_edge(
                    triage_node,
                    f"directive:{row['directive_id']}",
                    "prepared",
                    "prepared search",
                )

        for row in directives:
            directive_id = str(row["id"])
            add_node(
                f"directive:{directive_id}",
                "directive",
                str(row["title"]),
                detail=row["search_brief"],
                status=row["status"],
                timestamp=row["created_at"],
                approved_by=row["approved_by"],
                approved_at=row["approved_at"],
                attribution=row["attribution"],
            )
        for row in directive_leads:
            lead_id = str(row["lead_id"])
            directive_id = str(row["directive_id"])
            if lead_id in gap_ids and directive_id in directive_by_id:
                add_edge(
                    f"gap:{lead_id}",
                    f"directive:{directive_id}",
                    "investigated_by",
                    "investigated by",
                    attribution=directive_by_id[directive_id]["attribution"],
                )

        for row in dispatch_runs:
            dispatch_node = f"dispatch:{row['id']}"
            add_node(
                dispatch_node,
                "dispatch",
                f"Foundry search run {row['id']}",
                status=row["status"],
                provider=row["provider"],
                model=row["model"],
                timestamp=row["started_at"],
                completed_at=row["completed_at"],
                error_type=row["error_type"],
                error=row["error"],
            )
            add_edge(
                f"directive:{row['directive_id']}",
                dispatch_node,
                "executed_as",
                "executed as",
            )

        for candidate in self.candidates_with_decisions():
            related_gap_ids = gap_ids.intersection(
                str(item) for item in candidate.get("related_lead_ids", [])
            )
            if not related_gap_ids:
                continue
            candidate_id = str(candidate["id"])
            candidate_node = f"candidate:{candidate_id}"
            registration = candidate.get("canonical_registration")
            decision = candidate.get("latest_decision")
            add_node(
                candidate_node,
                "candidate",
                str(candidate["title"]),
                status=(
                    "registered"
                    if registration
                    else (
                        decision.get("action")
                        if isinstance(decision, dict)
                        else candidate.get("status")
                    )
                ),
                sha256=candidate.get("sha256"),
                source_url=candidate.get("source_url"),
                registration=registration,
            )
            for gap_id in sorted(related_gap_ids):
                add_edge(
                    f"gap:{gap_id}",
                    candidate_node,
                    "produced_candidate",
                    "produced candidate",
                    attribution="directive_scope",
                )

        return {
            "schema_version": 1,
            "question_run_id": question_run_id,
            "semantic_analysis_available": snapshot is not None,
            "nodes": nodes,
            "edges": edges,
        }

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

    def directive_context(self, directive_id: str) -> dict[str, object]:
        self.directive_store.get(directive_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT qr.id AS question_run_id, qr.question,
                       qr.created_at AS question_created_at,
                       dqr.attribution,
                       q.id AS gap_id,
                       COALESCE(qrg.description, q.description)
                         AS gap_description,
                       COALESCE(qrg.deciding_record, q.deciding_record)
                         AS deciding_record,
                       COALESCE(qrg.likely_custodian, q.likely_custodian)
                         AS likely_custodian,
                       qrg.rationale, qrg.related_claim_indices_json,
                       a.result_json
                  FROM research_directive_question_runs dqr
                  JOIN research_question_runs qr
                    ON qr.id = dqr.question_run_id
                  JOIN research_directive_leads dl
                    ON dl.directive_id = dqr.directive_id
                  JOIN research_question_run_gaps qrg
                    ON qrg.run_id = qr.id AND qrg.gap_id = dl.lead_id
                  JOIN research_queue q ON q.id = qrg.gap_id
                  LEFT JOIN research_question_analyses a
                    ON a.question_run_id = qr.id
                 WHERE dqr.directive_id = ?
                 ORDER BY qr.created_at, q.created_at, q.id
                """,
                (directive_id,),
            ).fetchall()
            triage_table = connection.execute(
                """
                SELECT 1
                  FROM sqlite_master
                 WHERE type = 'table' AND name = 'research_triage_runs'
                """
            ).fetchone()
            triage_columns = (
                {
                    str(row["name"])
                    for row in connection.execute(
                        "PRAGMA table_info(research_triage_runs)"
                    )
                }
                if triage_table is not None
                else set()
            )
            triage_row = (
                connection.execute(
                    """
                    SELECT output_json
                      FROM research_triage_runs
                     WHERE directive_id = ? AND status = 'completed'
                     ORDER BY id DESC
                     LIMIT 1
                    """,
                    (directive_id,),
                ).fetchone()
                if "directive_id" in triage_columns
                else None
            )

        questions: dict[str, dict[str, object]] = {}
        has_explicit_claim_link = False
        for row in rows:
            question_run_id = str(row["question_run_id"])
            question = questions.setdefault(
                question_run_id,
                {
                    "id": question_run_id,
                    "question": row["question"],
                    "created_at": row["question_created_at"],
                    "attribution": row["attribution"],
                    "semantic_analysis_available": row["result_json"] is not None,
                    "gaps": [],
                },
            )
            try:
                claim_indices = json.loads(
                    str(row["related_claim_indices_json"])
                )
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Gap claim relationships are corrupt for {row['gap_id']}"
                ) from error
            if not isinstance(claim_indices, list) or not all(
                isinstance(index, int) for index in claim_indices
            ):
                raise RuntimeError(
                    f"Gap claim relationships are invalid for {row['gap_id']}"
                )
            related_claims = []
            if row["result_json"] is not None:
                try:
                    snapshot = json.loads(str(row["result_json"]))
                except json.JSONDecodeError as error:
                    raise RuntimeError(
                        f"Question analysis is corrupt for {question_run_id}"
                    ) from error
                analysis = snapshot.get("analysis")
                claims = (
                    analysis.get("claims", [])
                    if isinstance(analysis, dict)
                    else []
                )
                for claim_index in claim_indices:
                    if claim_index < 0 or claim_index >= len(claims):
                        raise RuntimeError(
                            f"Gap {row['gap_id']} refers to missing claim "
                            f"{claim_index}"
                        )
                    claim = claims[claim_index]
                    related_claims.append(
                        {
                            "index": claim_index,
                            "text": claim.get("text"),
                            "does_not_establish": claim.get(
                                "does_not_establish"
                            ),
                        }
                    )
                has_explicit_claim_link = (
                    has_explicit_claim_link or bool(related_claims)
                )
            question["gaps"].append(
                {
                    "id": row["gap_id"],
                    "description": row["gap_description"],
                    "deciding_record": row["deciding_record"],
                    "likely_custodian": row["likely_custodian"],
                    "rationale": row["rationale"],
                    "related_claims": related_claims,
                    "unresolved_claim_indices": (
                        claim_indices if row["result_json"] is None else []
                    ),
                }
            )

        triage_rationale = None
        if triage_row is not None and triage_row["output_json"] is not None:
            try:
                triage_output = json.loads(str(triage_row["output_json"]))
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Triage output is corrupt for {directive_id}"
                ) from error
            triage_rationale = triage_output.get("rationale")

        attributions = {
            str(question["attribution"]) for question in questions.values()
        }
        if has_explicit_claim_link:
            relevance_basis = "explicit_claim_limit"
            caveat = (
                "The search is linked to specific persisted claim limitations. "
                "Relevance remains provisional until the retrieved record is "
                "validated."
            )
        elif "inferred_legacy" in attributions:
            relevance_basis = "legacy_inference"
            caveat = (
                "This workflow-to-question association was reconstructed from "
                "legacy timing and a shared gap. Review it skeptically before "
                "approval."
            )
        else:
            relevance_basis = "recorded_gap"
            caveat = (
                "The question and evidence gaps are recorded, but the earlier "
                "chat predates persisted claim text. Review whether the deciding "
                "records are material before approval."
            )
        return {
            "directive_id": directive_id,
            "relevance_basis": relevance_basis,
            "triage_rationale": triage_rationale,
            "caveat": caveat,
            "questions": list(questions.values()),
        }

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
            triage_configured = os.environ.get(
                "MENDO_TRIAGE_AUTOMATION_ENABLED",
                "false",
            ).lower() in {"1", "true", "yes"}
            triage_automation: dict[str, object] = {
                "configured": triage_configured,
                "state": "not_configured",
                "healthy": False,
                "heartbeat_at": None,
                "current_question_run_id": None,
                "current_triage_run_id": None,
                "last_error": None,
                "copilot_required": False,
            }
            if triage_configured:
                table_exists = connection.execute(
                    """
                    SELECT 1
                      FROM sqlite_master
                     WHERE type = 'table'
                       AND name = 'research_triage_worker_status'
                    """
                ).fetchone()
                status_row = (
                    connection.execute(
                        """
                        SELECT state, heartbeat_at, current_question_run_id,
                               current_triage_run_id, last_error
                          FROM research_triage_worker_status
                         WHERE id = 1
                        """
                    ).fetchone()
                    if table_exists
                    else None
                )
                if status_row is None:
                    triage_automation["state"] = "not_started"
                else:
                    heartbeat_at = str(status_row["heartbeat_at"])
                    poll_seconds = max(
                        int(os.environ.get("MENDO_TRIAGE_POLL_SECONDS", "30")),
                        1,
                    )
                    heartbeat_age = (
                        datetime.now(UTC)
                        - datetime.fromisoformat(heartbeat_at)
                    ).total_seconds()
                    healthy = heartbeat_age <= max(poll_seconds * 3, 120)
                    triage_automation.update(
                        {
                            "state": (
                                str(status_row["state"])
                                if healthy
                                else "stale"
                            ),
                            "healthy": healthy,
                            "heartbeat_at": heartbeat_at,
                            "current_question_run_id": status_row[
                                "current_question_run_id"
                            ],
                            "current_triage_run_id": status_row[
                                "current_triage_run_id"
                            ],
                            "last_error": status_row["last_error"],
                        }
                    )
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
            "triage_automation": triage_automation,
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
            if path == "/api/workbench/consultations":
                items = self.workbench_server.store.consultations()
                self._json(HTTPStatus.OK, {"items": items, "count": len(items)})
                return
            if path == "/api/workbench/provenance/questions":
                items = self.workbench_server.store.provenance_questions()
                self._json(HTTPStatus.OK, {"items": items, "count": len(items)})
                return
            provenance_match = re.fullmatch(
                r"/api/workbench/provenance/questions/([^/]+)", path
            )
            if provenance_match:
                self._json(
                    HTTPStatus.OK,
                    self.workbench_server.store.provenance_graph(
                        unquote(provenance_match.group(1))
                    ),
                )
                return
            if path == "/api/workbench/research-activity":
                items = self.workbench_server.store.research_activity()
                self._json(HTTPStatus.OK, {"items": items, "count": len(items)})
                return
            directive_context_match = re.fullmatch(
                r"/api/workbench/research-directives/([^/]+)/context",
                path,
            )
            if directive_context_match:
                self._json(
                    HTTPStatus.OK,
                    self.workbench_server.store.directive_context(
                        unquote(directive_context_match.group(1))
                    ),
                )
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
        if path == "/api/workbench/consultations":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if (
                    length <= 0
                    or length > MAX_DECISION_BYTES
                    or self.headers.get_content_type() != "application/json"
                ):
                    raise WorkbenchError("Invalid consultation request body")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise WorkbenchError("Consultation body must be an object")
                case_id = payload.get("case_id", "UM_2025-0004")
                kind = payload.get("kind")
                brief = payload.get("brief")
                if not all(isinstance(value, str) for value in (case_id, kind, brief)):
                    raise WorkbenchError("Consultation fields must be strings")
                content = {
                    name: payload.get(name, "")
                    for name in (
                        "markdown",
                        "html",
                        "analyst_context",
                        "journalist_context",
                        "architect_context",
                    )
                }
                actor = self.headers.get("X-Mendo-Workbench-User", "cio")
                result = self.workbench_server.store.create_consultation(
                    case_id, kind, brief, actor, **content
                )
                self._json(HTTPStatus.CREATED, result)
            except (ValueError, json.JSONDecodeError, WorkbenchError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        theorem_match = re.fullmatch(r"/api/workbench/consultations/([^/]+)/build", path)
        if theorem_match:
            try:
                result = self.workbench_server.store.build_theorem(unquote(theorem_match.group(1)))
                self._json(HTTPStatus.OK, result)
            except WorkbenchError as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
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
