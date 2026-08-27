"""Persistent Foundry triage for NFS-backed evidence-gap question runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from .config import Settings
from .providers import Reasoner, create_reasoner, provider_identity
from .research_dispatch import ResearchDirectiveStore
from .research_queue import ResearchQueue


class ResearchTriageError(RuntimeError):
    """A question run could not be converted into a safe disposition."""


class ResearchTriageOutputError(ResearchTriageError):
    """Foundry returned malformed or policy-invalid triage output."""


class ResearchTriageTransientError(ResearchTriageError):
    """A temporary provider failure interrupted triage."""


DEFAULT_ALLOWED_HOSTS = (
    "documents.coastal.ca.gov",
    "leginfo.legislature.ca.gov",
    "mccsd.com",
    "mendocinocounty.gov",
    "mendocinousd.org",
    "mendolafco.org",
    "municipalcodes.lexisnexis.com",
    "waterboards.ca.gov",
    "www.coastal.ca.gov",
    "www.mccsd.com",
    "www.mendocinocounty.gov",
    "www.mendocinousd.org",
    "www.mendolafco.org",
    "www.waterboards.ca.gov",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class TriageQuestion:
    run_id: str
    case_id: str
    question: str
    gaps: tuple[dict[str, str | None], ...]


@dataclass(frozen=True)
class TriagePlan:
    disposition: str
    rationale: str
    title: str | None = None
    search_brief: str | None = None
    allowed_hosts: tuple[str, ...] = ()


class TriageReasoner(Protocol):
    async def respond(self, role_id: str, instructions: str, prompt: str) -> str: ...


class ResearchTriageStore:
    def __init__(self, path: Path) -> None:
        if path.suffix == ".json":
            raise ResearchTriageError("Foundry triage requires a SQLite queue")
        self.path = path
        ResearchQueue(path)
        ResearchDirectiveStore(path)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_triage_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question_run_id TEXT NOT NULL,
                  status TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  model TEXT,
                  lead_ids_json TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  heartbeat_at TEXT NOT NULL,
                  completed_at TEXT,
                  output_json TEXT,
                  error_type TEXT,
                  error TEXT,
                  failure_class TEXT,
                  retry_after TEXT,
                  directive_id TEXT,
                  FOREIGN KEY (question_run_id)
                    REFERENCES research_question_runs(id)
                );
                CREATE TABLE IF NOT EXISTS research_triage_worker_status (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  state TEXT NOT NULL,
                  heartbeat_at TEXT NOT NULL,
                  current_question_run_id TEXT,
                  current_triage_run_id INTEGER,
                  last_error TEXT
                );
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(research_triage_runs)"
                )
            }
            if "failure_class" not in columns:
                connection.execute(
                    "ALTER TABLE research_triage_runs "
                    "ADD COLUMN failure_class TEXT"
                )
            if "retry_after" not in columns:
                connection.execute(
                    "ALTER TABLE research_triage_runs "
                    "ADD COLUMN retry_after TEXT"
                )
            if "directive_id" not in columns:
                connection.execute(
                    "ALTER TABLE research_triage_runs "
                    "ADD COLUMN directive_id TEXT"
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def recover_interrupted_runs(self) -> None:
        now = datetime.now(UTC)
        timestamp = now.isoformat()
        retry_after = (now + timedelta(seconds=30)).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE research_triage_runs
                   SET status = 'failed', completed_at = ?,
                       heartbeat_at = ?, error_type = 'WorkerRestart',
                       error = 'Triage worker restarted before completion',
                       failure_class = 'transient', retry_after = ?
                 WHERE status = 'running'
                """,
                (timestamp, timestamp, retry_after),
            )

    def heartbeat(
        self,
        state: str,
        *,
        question_run_id: str | None = None,
        triage_run_id: int | None = None,
        last_error: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_triage_worker_status
                  (id, state, heartbeat_at, current_question_run_id,
                   current_triage_run_id, last_error)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  state = excluded.state,
                  heartbeat_at = excluded.heartbeat_at,
                  current_question_run_id =
                    excluded.current_question_run_id,
                  current_triage_run_id = excluded.current_triage_run_id,
                  last_error = excluded.last_error
                """,
                (
                    state,
                    _now(),
                    question_run_id,
                    triage_run_id,
                    last_error,
                ),
            )

    def pending_directive_count(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                      FROM research_directives
                     WHERE status IN ('pending_approval', 'approved')
                    """
                ).fetchone()[0]
            )

    def next_question(self) -> TriageQuestion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT r.id, r.case_id, r.question
                  FROM research_question_runs r
                 WHERE EXISTS (
                         SELECT 1
                           FROM research_question_run_gaps g
                           JOIN research_queue q ON q.id = g.gap_id
                          WHERE g.run_id = r.id AND q.status = 'triage'
                       )
                   AND NOT EXISTS (
                         SELECT 1
                           FROM research_triage_runs t
                          WHERE t.question_run_id = r.id
                            AND t.status IN ('running', 'completed')
                       )
                   AND (
                         SELECT COUNT(*)
                           FROM research_triage_runs t
                          WHERE t.question_run_id = r.id
                            AND t.status = 'failed'
                            AND t.failure_class = 'output'
                       ) < 3
                   AND NOT EXISTS (
                         SELECT 1
                           FROM research_triage_runs retry
                          WHERE retry.question_run_id = r.id
                            AND retry.status = 'failed'
                            AND retry.failure_class = 'transient'
                            AND retry.retry_after > ?
                       )
                 ORDER BY
                   CASE WHEN (
                     SELECT COUNT(*) % 2 FROM research_triage_runs
                   ) = 0 THEN r.created_at END DESC,
                   CASE WHEN (
                     SELECT COUNT(*) % 2 FROM research_triage_runs
                   ) = 1 THEN r.created_at END ASC,
                   r.id ASC
                 LIMIT 1
                """,
                (_now(),),
            ).fetchone()
            if row is None:
                return None
            gaps = tuple(
                {
                    "id": str(gap["id"]),
                    "description": str(gap["description"]),
                    "deciding_record": str(gap["deciding_record"]),
                    "likely_custodian": (
                        str(gap["likely_custodian"])
                        if gap["likely_custodian"] is not None
                        else None
                    ),
                }
                for gap in connection.execute(
                    """
                    SELECT q.id, q.description, q.deciding_record,
                           q.likely_custodian
                      FROM research_question_run_gaps g
                      JOIN research_queue q ON q.id = g.gap_id
                     WHERE g.run_id = ? AND q.status = 'triage'
                     ORDER BY q.id
                    """,
                    (str(row["id"]),),
                )
            )
        return TriageQuestion(
            run_id=str(row["id"]),
            case_id=str(row["case_id"]),
            question=str(row["question"]),
            gaps=gaps,
        )

    def terminal_failure(self) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT t.error
                  FROM research_triage_runs t
                 WHERE t.status = 'failed'
                   AND t.failure_class = 'output'
                   AND (
                         SELECT COUNT(*)
                           FROM research_triage_runs attempts
                          WHERE attempts.question_run_id = t.question_run_id
                            AND attempts.status = 'failed'
                            AND attempts.failure_class = 'output'
                       ) >= 3
                   AND EXISTS (
                         SELECT 1
                           FROM research_question_run_gaps g
                           JOIN research_queue q ON q.id = g.gap_id
                          WHERE g.run_id = t.question_run_id
                            AND q.status = 'triage'
                       )
                 ORDER BY t.id DESC
                 LIMIT 1
                """
            ).fetchone()
        return str(row["error"]) if row is not None else None

    def retry_backoff(self) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT error
                  FROM research_triage_runs
                 WHERE status = 'failed'
                   AND failure_class = 'transient'
                   AND retry_after > ?
                 ORDER BY retry_after DESC
                 LIMIT 1
                """,
                (_now(),),
            ).fetchone()
        return str(row["error"]) if row is not None else None

    def start(
        self,
        question: TriageQuestion,
        provider: str,
        model: str | None,
    ) -> int:
        timestamp = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            already_claimed = connection.execute(
                """
                SELECT 1
                  FROM research_triage_runs
                 WHERE question_run_id = ?
                   AND status IN ('running', 'completed')
                 LIMIT 1
                """,
                (question.run_id,),
            ).fetchone()
            if already_claimed is not None:
                raise ResearchTriageError(
                    f"Question run {question.run_id} is already claimed"
                )
            cursor = connection.execute(
                """
                INSERT INTO research_triage_runs
                  (question_run_id, status, provider, model, lead_ids_json,
                   started_at, heartbeat_at)
                VALUES (?, 'running', ?, ?, ?, ?, ?)
                """,
                (
                    question.run_id,
                    provider,
                    model,
                    json.dumps([gap["id"] for gap in question.gaps]),
                    timestamp,
                    timestamp,
                ),
            )
            return int(cursor.lastrowid)

    def apply_plan(
        self,
        run_id: int,
        question: TriageQuestion,
        plan: TriagePlan,
        directive_store: ResearchDirectiveStore,
        max_pending_directives: int,
    ) -> None:
        timestamp = _now()
        with self._connect() as connection:
            lead_ids = tuple(str(gap["id"]) for gap in question.gaps)
            placeholders = ",".join("?" for _ in lead_ids)
            triage_count = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                      FROM research_queue
                     WHERE status = 'triage'
                       AND id IN ({placeholders})
                    """,
                    lead_ids,
                ).fetchone()[0]
            )
            if triage_count != len(lead_ids):
                raise ResearchTriageError(
                    "Gap state changed during triage; disposition refused"
                )
            directive_id = None
            if plan.disposition == "prepare_search":
                pending_count = int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                          FROM research_directives
                         WHERE status IN ('pending_approval', 'approved')
                        """
                    ).fetchone()[0]
                )
                if pending_count >= max_pending_directives:
                    raise ResearchTriageError(
                        "CIO approval backpressure cap was reached during "
                        "triage; directive creation deferred"
                    )
                directive_id = directive_store.create_in_transaction(
                    connection,
                    question.case_id,
                    plan.title or "",
                    plan.search_brief or "",
                    lead_ids,
                    plan.allowed_hosts,
                    question_run_id=question.run_id,
                )
            else:
                cursor = connection.execute(
                    f"""
                    UPDATE research_queue
                       SET status = ?
                     WHERE status = 'triage'
                       AND id IN ({placeholders})
                    """,
                    (plan.disposition, *lead_ids),
                )
                if cursor.rowcount != len(lead_ids):
                    raise ResearchTriageError(
                        "Gap state changed during triage; disposition refused"
                    )
            cursor = connection.execute(
                """
                UPDATE research_triage_runs
                   SET status = 'completed', heartbeat_at = ?,
                       completed_at = ?, output_json = ?,
                       directive_id = ?,
                       error_type = NULL, error = NULL,
                       failure_class = NULL, retry_after = NULL
                 WHERE id = ? AND status = 'running'
                """,
                (
                    timestamp,
                    timestamp,
                    json.dumps(asdict(plan), sort_keys=True),
                    directive_id,
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ResearchTriageError(
                    f"Triage run {run_id} was not running at completion"
                )

    def fail(self, run_id: int, error: Exception) -> bool:
        now = datetime.now(UTC)
        timestamp = now.isoformat()
        failure_class = (
            "output"
            if isinstance(error, ResearchTriageOutputError)
            else "transient"
        )
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT question_run_id
                  FROM research_triage_runs
                 WHERE id = ? AND status = 'running'
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                raise ResearchTriageError(
                    f"Triage run {run_id} was not running at failure"
                )
            transient_attempts = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                      FROM research_triage_runs
                     WHERE question_run_id = ?
                       AND status = 'failed'
                       AND failure_class = 'transient'
                    """,
                    (str(row["question_run_id"]),),
                ).fetchone()[0]
            )
            retry_after = (
                now
                + timedelta(
                    seconds=min(30 * (2 ** transient_attempts), 1800)
                )
            ).isoformat() if failure_class == "transient" else None
            cursor = connection.execute(
                """
                UPDATE research_triage_runs
                   SET status = 'failed', heartbeat_at = ?, completed_at = ?,
                       error_type = ?, error = ?, failure_class = ?,
                       retry_after = ?
                 WHERE id = ? AND status = 'running'
                """,
                (
                    timestamp,
                    timestamp,
                    type(error).__name__,
                    str(error)[:4000],
                    failure_class,
                    retry_after,
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ResearchTriageError(
                    f"Triage run {run_id} was not running at failure"
                )
            if failure_class == "output":
                output_attempts = int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                          FROM research_triage_runs
                         WHERE question_run_id = ?
                           AND status = 'failed'
                           AND failure_class = 'output'
                        """,
                        (str(row["question_run_id"]),),
                    ).fetchone()[0]
                )
                return output_attempts >= 3
        return False

class FoundryTriageWorker:
    def __init__(
        self,
        store: ResearchTriageStore,
        reasoner: TriageReasoner,
        *,
        provider: str,
        allowed_hosts: tuple[str, ...],
        max_pending_directives: int = 3,
        request_timeout_seconds: float = 300,
        heartbeat_seconds: float = 30,
    ) -> None:
        if max_pending_directives < 1:
            raise ValueError("max_pending_directives must be positive")
        normalized_hosts = tuple(
            sorted({host.strip().lower() for host in allowed_hosts if host.strip()})
        )
        if not normalized_hosts:
            raise ValueError("Foundry triage requires approved official hosts")
        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        self.store = store
        self.reasoner = reasoner
        self.provider = provider
        self.allowed_hosts = normalized_hosts
        self.max_pending_directives = max_pending_directives
        self.request_timeout_seconds = request_timeout_seconds
        self.heartbeat_seconds = min(
            heartbeat_seconds,
            request_timeout_seconds,
        )
        self.directive_store = ResearchDirectiveStore(store.path)

    async def process_one(self) -> bool:
        if (
            self.store.pending_directive_count()
            >= self.max_pending_directives
        ):
            self.store.heartbeat("waiting_for_cio")
            return False
        question = self.store.next_question()
        if question is None:
            terminal_failure = self.store.terminal_failure()
            retry_backoff = self.store.retry_backoff()
            self.store.heartbeat(
                (
                    "failed"
                    if terminal_failure
                    else "retry_backoff"
                    if retry_backoff
                    else "idle"
                ),
                last_error=terminal_failure or retry_backoff,
            )
            return False
        identity = provider_identity(self.provider)
        try:
            run_id = self.store.start(
                question,
                str(identity["provider"]),
                identity["model"],
            )
        except ResearchTriageError:
            return False
        self.store.heartbeat(
            "running",
            question_run_id=question.run_id,
            triage_run_id=run_id,
        )
        try:
            raw = await self._respond(question, run_id)
            plan = self._parse(raw)
            self.store.apply_plan(
                run_id,
                question,
                plan,
                self.directive_store,
                self.max_pending_directives,
            )
            self.store.heartbeat("idle")
            print(
                json.dumps(
                    {
                        "event": "triage_completed",
                        "question_run_id": question.run_id,
                        "triage_run_id": run_id,
                        "disposition": plan.disposition,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            return True
        except Exception as error:
            terminal = self.store.fail(run_id, error)
            self.store.heartbeat(
                "failed" if terminal else "retry_backoff",
                last_error=str(error)[:4000],
            )
            print(
                json.dumps(
                    {
                        "event": "triage_failed",
                        "question_run_id": question.run_id,
                        "triage_run_id": run_id,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            return False

    async def _respond(
        self,
        question: TriageQuestion,
        run_id: int,
    ) -> str:
        async def maintain_heartbeat() -> None:
            while True:
                await asyncio.sleep(self.heartbeat_seconds)
                self.store.heartbeat(
                    "running",
                    question_run_id=question.run_id,
                    triage_run_id=run_id,
                )

        heartbeat = asyncio.create_task(maintain_heartbeat())
        try:
            return await asyncio.wait_for(
                self.reasoner.respond(
                    "research-triage",
                    self._instructions(),
                    self._prompt(question),
                ),
                timeout=self.request_timeout_seconds,
            )
        except TimeoutError as error:
            raise ResearchTriageTransientError(
                "Foundry triage exceeded the configured request timeout"
            ) from error
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat

    def _instructions(self) -> str:
        return (
            "You are the Foundry Research Triage role. Convert a set of "
            "evidence gaps from one public-interest question into exactly one "
            "bounded disposition. You do not search the web, approve work, "
            "treat your output as evidence, or weaken source controls. Prefer "
            "one focused official-source search for gaps that can be resolved "
            "together. Use requires_transaction_identification only when the "
            "missing record cannot be identified without a specific proposed "
            "transaction, recipient, location, or date. Never claim that a "
            "record is already in the corpus; this role has no deterministic "
            "corpus lookup. Return only strict JSON."
        )

    def _prompt(self, question: TriageQuestion) -> str:
        schema = {
            "disposition": (
                "prepare_search | requires_transaction_identification"
            ),
            "rationale": "short explanation",
            "title": "required only for prepare_search",
            "search_brief": "required only for prepare_search",
            "allowed_hosts": [
                "one or more exact hosts from approved_allowed_hosts"
            ],
        }
        return json.dumps(
            {
                "task": (
                    "Classify all supplied gaps together. For prepare_search, "
                    "write a bounded brief naming the deciding records and "
                    "official custodians; select only necessary approved hosts."
                ),
                "question_run_id": question.run_id,
                "question": question.question,
                "gaps": question.gaps,
                "approved_allowed_hosts": self.allowed_hosts,
                "response_schema": schema,
            },
            sort_keys=True,
        )

    def _parse(self, raw: str) -> TriagePlan:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ResearchTriageOutputError(
                "Foundry triage returned non-JSON output"
            ) from error
        if not isinstance(value, dict):
            raise ResearchTriageOutputError(
                "Foundry triage output must be an object"
            )
        disposition = value.get("disposition")
        allowed_dispositions = {
            "prepare_search",
            "requires_transaction_identification",
        }
        if disposition not in allowed_dispositions:
            raise ResearchTriageOutputError(
                f"Foundry triage returned invalid disposition: {disposition}"
            )
        rationale = value.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ResearchTriageOutputError(
                "Foundry triage must provide a rationale"
            )
        if disposition != "prepare_search":
            return TriagePlan(
                disposition=str(disposition),
                rationale=rationale.strip(),
            )
        title = value.get("title")
        brief = value.get("search_brief")
        hosts = value.get("allowed_hosts")
        if not isinstance(title, str) or not title.strip():
            raise ResearchTriageOutputError(
                "Foundry triage search title is missing"
            )
        if not isinstance(brief, str) or not brief.strip():
            raise ResearchTriageOutputError(
                "Foundry triage search brief is missing"
            )
        if (
            not isinstance(hosts, list)
            or not hosts
            or not all(isinstance(host, str) for host in hosts)
        ):
            raise ResearchTriageOutputError(
                "Foundry triage must select approved official hosts"
            )
        normalized_hosts = tuple(
            sorted({host.strip().lower() for host in hosts if host.strip()})
        )
        unapproved = sorted(set(normalized_hosts) - set(self.allowed_hosts))
        if unapproved:
            raise ResearchTriageOutputError(
                "Foundry triage selected unapproved hosts: "
                + ", ".join(unapproved)
            )
        return TriagePlan(
            disposition="prepare_search",
            rationale=rationale.strip(),
            title=" ".join(title.split()),
            search_brief=" ".join(brief.split()),
            allowed_hosts=normalized_hosts,
        )


async def run_worker(
    worker: FoundryTriageWorker,
    *,
    poll_seconds: float,
) -> None:
    if poll_seconds < 1:
        raise ValueError("poll_seconds must be at least one second")
    worker.store.recover_interrupted_runs()
    worker.store.heartbeat("starting")
    while True:
        await worker.process_one()
        await asyncio.sleep(poll_seconds)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-triage-worker")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--provider",
        choices=("scripted", "ollama", "foundry"),
        default=None,
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=float(os.environ.get("MENDO_TRIAGE_POLL_SECONDS", "30")),
    )
    parser.add_argument(
        "--max-pending-directives",
        type=int,
        default=int(os.environ.get("MENDO_TRIAGE_MAX_PENDING", "3")),
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=float(
            os.environ.get("MENDO_TRIAGE_REQUEST_TIMEOUT_SECONDS", "300")
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = Settings.from_env(args.repo_root)
    provider = args.provider or settings.model_provider
    if provider != "foundry":
        raise RuntimeError(
            "Persistent research triage requires the Foundry provider"
        )
    configured_hosts = os.environ.get("MENDO_TRIAGE_ALLOWED_HOSTS")
    allowed_hosts = (
        tuple(configured_hosts.split(","))
        if configured_hosts
        else DEFAULT_ALLOWED_HOSTS
    )
    store = ResearchTriageStore(settings.research_queue_path)
    worker = FoundryTriageWorker(
        store,
        create_reasoner(provider),
        provider=provider,
        allowed_hosts=allowed_hosts,
        max_pending_directives=args.max_pending_directives,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    asyncio.run(run_worker(worker, poll_seconds=args.poll_seconds))


if __name__ == "__main__":
    main()
