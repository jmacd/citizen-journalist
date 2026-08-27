"""Foundry-assisted diagnosis of terminal public-record retrieval failures."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import urldefrag

from .models import AcquisitionDiagnosis, RetrievalFailure


class AcquisitionEngineeringError(RuntimeError):
    """Raised when a retrieval failure cannot be diagnosed safely."""


class FailureDiagnoser(Protocol):
    def diagnose(self, failure: RetrievalFailure) -> AcquisitionDiagnosis: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


class AcquisitionEngineeringStore:
    def __init__(self, queue_path: Path) -> None:
        self.path = queue_path
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS acquisition_diagnoses (
                  id TEXT PRIMARY KEY,
                  run_id INTEGER NOT NULL UNIQUE,
                  directive_id TEXT NOT NULL,
                  failure_kind TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  root_cause TEXT NOT NULL,
                  repair_kind TEXT NOT NULL,
                  code_change_required INTEGER NOT NULL,
                  proposed_changes_json TEXT NOT NULL,
                  safety_constraints_json TEXT NOT NULL,
                  citations_json TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  model TEXT NOT NULL,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (run_id) REFERENCES research_dispatch_runs(id),
                  FOREIGN KEY (directive_id) REFERENCES research_directives(id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def failure(self, run_id: int) -> RetrievalFailure:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT r.id, r.directive_id, r.status, r.completed_at,
                       r.error_type, r.error, r.directive_snapshot_json,
                       d.case_id, d.title, d.search_brief,
                       d.allowed_hosts_json
                  FROM research_dispatch_runs r
                  JOIN research_directives d ON d.id = r.directive_id
                 WHERE r.id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            raise AcquisitionEngineeringError(
                f"Unknown research dispatch run: {run_id}"
            )
        if str(row["status"]) != "failed" or not row["error"]:
            raise AcquisitionEngineeringError(
                f"Research dispatch run {run_id} is not a terminal failure"
            )
        message = str(row["error"])
        snapshot = (
            json.loads(str(row["directive_snapshot_json"]))
            if row["directive_snapshot_json"]
            else None
        )
        return RetrievalFailure(
            run_id=int(row["id"]),
            directive_id=str(row["directive_id"]),
            case_id=str(row["case_id"]),
            directive_title=str(
                snapshot["title"] if snapshot is not None else row["title"]
            ),
            search_brief=str(
                snapshot["search_brief"]
                if snapshot is not None
                else row["search_brief"]
            ),
            allowed_hosts=(
                tuple(str(item) for item in snapshot["allowed_hosts"])
                if snapshot is not None
                else ()
            ),
            error_type=str(row["error_type"] or "legacy_failure"),
            error_message=message,
            failed_at=str(row["completed_at"]),
            directive_snapshot_status=(
                "captured_at_dispatch"
                if snapshot is not None
                else "unavailable_legacy_run"
            ),
        )

    def record(self, diagnosis: AcquisitionDiagnosis) -> AcquisitionDiagnosis:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO acquisition_diagnoses
                  (id, run_id, directive_id, failure_kind, summary, root_cause,
                   repair_kind, code_change_required, proposed_changes_json,
                   safety_constraints_json, citations_json, provider, model,
                   status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    diagnosis.id,
                    diagnosis.run_id,
                    diagnosis.directive_id,
                    diagnosis.failure_kind,
                    diagnosis.summary,
                    diagnosis.root_cause,
                    diagnosis.repair_kind,
                    int(diagnosis.code_change_required),
                    json.dumps(diagnosis.proposed_changes, sort_keys=True),
                    json.dumps(diagnosis.safety_constraints),
                    json.dumps(diagnosis.citations),
                    diagnosis.provider,
                    diagnosis.model,
                    diagnosis.status,
                    diagnosis.created_at,
                ),
            )
        return diagnosis

    def get_for_run(self, run_id: int) -> AcquisitionDiagnosis | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM acquisition_diagnoses WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return self._decode(row) if row is not None else None

    def list(self) -> tuple[AcquisitionDiagnosis, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM acquisition_diagnoses ORDER BY created_at DESC"
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

    @staticmethod
    def _decode(row: sqlite3.Row) -> AcquisitionDiagnosis:
        return AcquisitionDiagnosis(
            id=str(row["id"]),
            run_id=int(row["run_id"]),
            directive_id=str(row["directive_id"]),
            failure_kind=str(row["failure_kind"]),
            summary=str(row["summary"]),
            root_cause=str(row["root_cause"]),
            repair_kind=str(row["repair_kind"]),
            code_change_required=bool(row["code_change_required"]),
            proposed_changes=tuple(
                dict(item) for item in json.loads(str(row["proposed_changes_json"]))
            ),
            safety_constraints=tuple(
                str(item)
                for item in json.loads(str(row["safety_constraints_json"]))
            ),
            citations=tuple(
                str(item) for item in json.loads(str(row["citations_json"]))
            ),
            provider=str(row["provider"]),
            model=str(row["model"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
        )


class FoundryAcquisitionEngineer:
    _FAILURE_KINDS = {
        "prompt_contract",
        "citation_ledger",
        "host_allowlist",
        "candidate_limit",
        "repository_access",
        "download",
        "identity_validation",
        "mime_validation",
        "parser",
        "workflow",
        "unknown",
    }
    _REPAIR_KINDS = {
        "directive_revision",
        "allowlist_revision",
        "deterministic_adapter",
        "parser_change",
        "validation_change",
        "workflow_change",
        "no_change",
        "blocked",
    }
    _SAFE_CODE_ROOTS = (
        PurePosixPath("agents/src/mendo_agents/repository_adapters"),
        PurePosixPath("agents/tests/repository_adapters"),
    )

    def __init__(self) -> None:
        if os.environ.get("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            raise AcquisitionEngineeringError(
                "Set MENDO_FOUNDRY_WEB_SEARCH_ENABLED=true to acknowledge "
                "Foundry web-search cost and external Bing data processing"
            )
        self.endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
        self.model = os.environ.get("FOUNDRY_MODEL", "")
        if not self.endpoint or not self.model:
            raise AcquisitionEngineeringError(
                "FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL are required"
            )

    def diagnose(self, failure: RetrievalFailure) -> AcquisitionDiagnosis:
        try:
            from azure.ai.projects import AIProjectClient
            from azure.ai.projects.models import PromptAgentDefinition, WebSearchTool
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise AcquisitionEngineeringError(
                "Foundry acquisition-engineering dependencies are not installed"
            ) from error

        instructions = (
            "You are the Acquisition Engineer for an auditable public-record "
            "system. Diagnose one terminal retrieval failure. You may research "
            "official repository behavior with web search, but web results are "
            "diagnostic context and never evidence. Do not weaken HTTPS, public "
            "DNS/IP checks, redirect checks, host allowlists, MIME validation, "
            "hashing, duplicate detection, citation-ledger enforcement, or CIO "
            "approval. Do not propose canonical evidence mutation, deployment, "
            "self-merge, access-control bypass, or public-record requests. "
            "Return strict JSON only with keys failure_kind, summary, root_cause, "
            "repair_kind, code_change_required, proposed_changes, "
            "safety_constraints, and citations. proposed_changes must be an "
            "array of objects with type, path, and description strings. If code "
            "is required, paths may only be new files beneath "
            "agents/src/mendo_agents/repository_adapters/ or "
            "agents/tests/repository_adapters/. Otherwise use an empty path. "
            "Allowed failure_kind values: "
            f"{', '.join(sorted(self._FAILURE_KINDS))}. Allowed repair_kind "
            f"values: {', '.join(sorted(self._REPAIR_KINDS))}."
        )
        prompt = json.dumps(asdict(failure), indent=2, sort_keys=True)
        project = AIProjectClient(
            endpoint=self.endpoint,
            credential=DefaultAzureCredential(
                exclude_interactive_browser_credential=True
            ),
        )
        agent = project.agents.create_version(
            agent_name="mendo-acquisition-engineer",
            definition=PromptAgentDefinition(
                model=self.model,
                instructions=instructions,
                tools=[WebSearchTool()],
            ),
            description="Ephemeral retrieval-failure diagnostician",
        )
        try:
            response = project.get_openai_client().responses.create(
                input=prompt,
                extra_body={
                    "agent_reference": {
                        "name": agent.name,
                        "type": "agent_reference",
                    }
                },
            )
            citations = self._citations(response)
            return self._parse(failure, response.output_text, citations)
        finally:
            project.agents.delete_version(
                agent_name=agent.name,
                agent_version=agent.version,
            )

    def _parse(
        self,
        failure: RetrievalFailure,
        raw: str,
        foundry_citations: tuple[str, ...],
    ) -> AcquisitionDiagnosis:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AcquisitionEngineeringError(
                "Acquisition Engineer returned non-JSON output"
            ) from error
        if not isinstance(value, dict):
            raise AcquisitionEngineeringError(
                "Acquisition Engineer output must be an object"
            )
        failure_kind = self._choice(
            value, "failure_kind", self._FAILURE_KINDS
        )
        repair_kind = self._choice(value, "repair_kind", self._REPAIR_KINDS)
        summary = self._text(value, "summary")
        root_cause = self._text(value, "root_cause")
        code_required = value.get("code_change_required")
        if not isinstance(code_required, bool):
            raise AcquisitionEngineeringError(
                "code_change_required must be a boolean"
            )
        changes = value.get("proposed_changes")
        if not isinstance(changes, list) or len(changes) > 10:
            raise AcquisitionEngineeringError(
                "proposed_changes must be an array of at most 10 items"
            )
        normalized_changes = tuple(
            self._change(item, code_required) for item in changes
        )
        constraints = self._string_array(value, "safety_constraints", 20)
        cited = self._string_array(value, "citations", 20)
        citation_ledger = {
            urldefrag(item)[0].rstrip("/") for item in foundry_citations
        }
        for url in cited:
            if urldefrag(url)[0].rstrip("/") not in citation_ledger:
                raise AcquisitionEngineeringError(
                    f"Diagnosis cites a URL absent from Foundry citations: {url}"
                )
        identity = f"{failure.run_id}\n{raw}"
        return AcquisitionDiagnosis(
            id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
            run_id=failure.run_id,
            directive_id=failure.directive_id,
            failure_kind=failure_kind,
            summary=summary,
            root_cause=root_cause,
            repair_kind=repair_kind,
            code_change_required=code_required,
            proposed_changes=normalized_changes,
            safety_constraints=constraints,
            citations=cited,
            provider="microsoft_foundry",
            model=self.model,
            status="diagnosis_pending_review",
            created_at=_now(),
        )

    def _change(
        self, value: object, code_required: bool
    ) -> dict[str, str]:
        if not isinstance(value, dict):
            raise AcquisitionEngineeringError(
                "Every proposed change must be an object"
            )
        change = {
            name: self._text(value, name)
            for name in ("type", "path", "description")
        }
        if code_required:
            path = PurePosixPath(change["path"])
            if path.is_absolute() or ".." in path.parts or not any(
                path.is_relative_to(root) for root in self._SAFE_CODE_ROOTS
            ):
                raise AcquisitionEngineeringError(
                    f"Proposed code path is outside the isolated adapter scope: {path}"
                )
        elif change["path"]:
            raise AcquisitionEngineeringError(
                "Non-code repairs must not propose repository file paths"
            )
        return change

    @staticmethod
    def _text(value: dict[str, object], name: str) -> str:
        item = value.get(name)
        if not isinstance(item, str):
            raise AcquisitionEngineeringError(f"{name} must be a string")
        return " ".join(item.split())

    @classmethod
    def _choice(
        cls, value: dict[str, object], name: str, choices: set[str]
    ) -> str:
        item = cls._text(value, name)
        if item not in choices:
            raise AcquisitionEngineeringError(
                f"{name} has unsupported value: {item}"
            )
        return item

    @staticmethod
    def _string_array(
        value: dict[str, object], name: str, limit: int
    ) -> tuple[str, ...]:
        items = value.get(name)
        if not isinstance(items, list) or len(items) > limit or not all(
            isinstance(item, str) and item.strip() for item in items
        ):
            raise AcquisitionEngineeringError(
                f"{name} must be an array of at most {limit} nonempty strings"
            )
        return tuple(str(item).strip() for item in items)

    @staticmethod
    def _citations(response: object) -> tuple[str, ...]:
        urls: set[str] = set()
        for output in getattr(response, "output", ()) or ():
            for content in getattr(output, "content", ()) or ():
                for annotation in getattr(content, "annotations", ()) or ():
                    url = getattr(annotation, "url", None)
                    if isinstance(url, str) and url:
                        urls.add(url)
        return tuple(sorted(urls))


class ResearchRecoveryOrchestrator:
    def __init__(
        self,
        store: AcquisitionEngineeringStore,
        diagnoser: FailureDiagnoser,
    ) -> None:
        self.store = store
        self.diagnoser = diagnoser

    def diagnose(self, run_id: int) -> AcquisitionDiagnosis:
        existing = self.store.get_for_run(run_id)
        if existing is not None:
            return existing
        failure = self.store.failure(run_id)
        return self.store.record(self.diagnoser.diagnose(failure))
