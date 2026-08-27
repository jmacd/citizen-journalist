"""Read-only public chat service over the canonical case corpus."""

from __future__ import annotations

import argparse
import asyncio
import json
from uuid import uuid4
import mimetypes
import traceback
from dataclasses import asdict, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import TypedDict
from urllib.parse import urlsplit

from agent_framework import FileCheckpointStorage

from .config import Settings
from .models import (
    CaseQuestion,
    Claim,
    DispositionKind,
    EvidenceGap,
    RunDisposition,
)
from .policy import load_society_policy
from .providers import create_reasoner, provider_identity
from .repository import CorpusRepository
from .research_queue import ResearchQueue
from .skills import load_skills
from .telemetry import configure_telemetry
from .workflow import build_evidence_workflow

MAX_REQUEST_BYTES = 16_384
MAX_QUESTION_CHARACTERS = 2_000
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARACTERS = 8_000


class ChatHistoryMessage(TypedDict):
    role: str
    content: str


class PublicChatError(RuntimeError):
    """A safe error that may be returned to a public client."""


class PublicChatService:
    def __init__(
        self,
        settings: Settings,
        *,
        policy_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.corpus = CorpusRepository(settings.repo_root, settings.case_id)
        self.policy = load_society_policy(
            policy_path
            or settings.repo_root / "agents" / "organization" / "society.yaml"
        )
        self.skills = load_skills(settings.repo_root)
        self.research_queue = ResearchQueue(settings.research_queue_path)
        self.telemetry = configure_telemetry(False)

    async def ask(
        self,
        question: str,
        history: tuple[ChatHistoryMessage, ...] = (),
    ) -> dict[str, object]:
        started_at = perf_counter()
        normalized = " ".join(question.split())
        if not normalized:
            raise PublicChatError("Enter a question about this case.")
        if len(normalized) > MAX_QUESTION_CHARACTERS:
            raise PublicChatError(
                f"Question exceeds {MAX_QUESTION_CHARACTERS} characters."
            )
        normalized_history = self._normalize_history(history)
        origin_run_id = str(uuid4())
        contextual_question = self._contextual_question(
            normalized,
            normalized_history,
        )
        self.telemetry.run_started(self.settings.case_id, "PublicCaseQuestion")

        checkpoint_path = (
            self.settings.checkpoint_root / "public-chat" / self.settings.case_id
        )
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        workflow = build_evidence_workflow(
            self.corpus,
            self.policy,
            self.skills,
            create_reasoner(self.settings.model_provider),
            FileCheckpointStorage(storage_path=checkpoint_path),
            max_iterations=self.settings.max_iterations,
            max_research_rounds=0,
            auto_publish_read_only=True,
            max_review_revisions=2,
        )
        output: RunDisposition | None = None
        async for event in workflow.run(
            CaseQuestion(
                case_id=self.settings.case_id,
                question=contextual_question,
                asked_by="public",
            ),
            stream=True,
        ):
            if event.type == "request_info":
                raise RuntimeError(
                    "Public read-only workflow unexpectedly requested approval"
                )
            if event.type == "output":
                output = event.data
        if output is None:
            raise RuntimeError("Public workflow ended without a disposition")
        public_gaps = self._public_gaps(output)
        queue_gaps = ()
        if output.analysis is not None and output.review is not None and (
            (
                output.kind == DispositionKind.ANSWER_READY
                and output.review.accepted
            )
            or (
                output.kind == DispositionKind.BLOCKED
                and not output.review.accepted
            )
        ):
            queue_gaps = public_gaps
        result = self._serialize(output)
        runtime = provider_identity(self.settings.model_provider)
        provenance_snapshot = self._provenance_snapshot(
            output,
            normalized,
            contextual_question,
            normalized_history,
            runtime,
        )
        queued = self.research_queue.enqueue(
            self.settings.case_id,
            normalized,
            queue_gaps,
            origin_type="foundry_public_chat",
            origin_run_id=origin_run_id,
            initiating_actor="public_cio",
            provenance_snapshot=provenance_snapshot,
        )
        result["queued_research"] = [asdict(item) for item in queued]
        result["runtime"] = runtime
        self.telemetry.run_completed(output.kind.value)
        print(
            json.dumps(
                {
                    "case_id": self.settings.case_id,
                    "claim_count": len(output.analysis.claims)
                    if output.analysis is not None
                    else 0,
                    "disposition": output.kind.value,
                    "duration_ms": round((perf_counter() - started_at) * 1000),
                    "event": "public_chat_completed",
                    "provider": runtime["provider"],
                    "queued_research_count": len(queued),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return result

    def _provenance_snapshot(
        self,
        output: RunDisposition,
        submitted_question: str,
        contextual_question: str,
        history: tuple[ChatHistoryMessage, ...],
        runtime: dict[str, str | None],
    ) -> dict[str, object]:
        analysis = output.analysis
        review = output.review
        return {
            "schema_version": 1,
            "submitted_question": submitted_question,
            "contextual_question": contextual_question,
            "conversation_context": [dict(message) for message in history],
            "disposition": output.kind.value,
            "summary": output.summary,
            "runtime": runtime,
            "analysis": (
                {
                    "short_answer": analysis.short_answer,
                    "claims": [
                        self._serialize_claims(
                            (claim,),
                            allow_invalid_locators=(
                                not (
                                    output.kind
                                    == DispositionKind.ANSWER_READY
                                    and review is not None
                                    and review.accepted
                                )
                                or index
                                not in analysis.answer_claim_indices
                            ),
                        )[0]
                        for index, claim in enumerate(analysis.claims)
                    ],
                    "answer_claim_indices": list(
                        analysis.answer_claim_indices
                    ),
                    "conclusion_kind": analysis.conclusion_kind,
                    "scope_statement": analysis.scope_statement,
                    "gaps": [asdict(gap) for gap in analysis.gaps],
                    "rules": [asdict(rule) for rule in analysis.rules],
                    "watches": [asdict(watch) for watch in analysis.watches],
                    "request_drafts": [
                        asdict(draft) for draft in analysis.request_drafts
                    ],
                }
                if analysis is not None
                else None
            ),
            "review": (
                {
                    "accepted": review.accepted,
                    "findings": [
                        asdict(finding) for finding in review.findings
                    ],
                    "targeted_gaps": [
                        asdict(gap) for gap in review.targeted_gaps
                    ],
                }
                if review is not None
                else None
            ),
        }

    @staticmethod
    def _normalize_history(
        history: tuple[ChatHistoryMessage, ...],
    ) -> tuple[ChatHistoryMessage, ...]:
        if len(history) > MAX_HISTORY_MESSAGES:
            raise PublicChatError(
                f"Conversation history exceeds {MAX_HISTORY_MESSAGES} messages."
            )
        normalized: list[ChatHistoryMessage] = []
        total_characters = 0
        for message in history:
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str):
                raise PublicChatError(
                    "Conversation history must contain user or assistant messages."
                )
            text = " ".join(content.split())
            if not text:
                raise PublicChatError(
                    "Conversation history cannot contain empty messages."
                )
            total_characters += len(text)
            if total_characters > MAX_HISTORY_CHARACTERS:
                raise PublicChatError(
                    "Conversation history is too long; start a new conversation."
                )
            normalized.append({"role": role, "content": text})
        return tuple(normalized)

    @staticmethod
    def _contextual_question(
        question: str,
        history: tuple[ChatHistoryMessage, ...],
    ) -> str:
        if not history:
            return question
        transcript = "\n".join(
            f"{message['role'].title()}: {message['content']}"
            for message in history
        )
        return f"Conversation context:\n{transcript}\nCurrent question: {question}"

    def _serialize(self, output: RunDisposition) -> dict[str, object]:
        if output.kind != DispositionKind.ANSWER_READY or output.analysis is None:
            withheld_claims = (
                self._serialize_claims(
                    output.analysis.claims,
                    allow_invalid_locators=True,
                )
                if output.analysis is not None
                else []
            )
            return {
                "status": output.kind.value,
                "summary": output.summary,
                "conclusion_kind": (
                    output.analysis.conclusion_kind
                    if output.analysis is not None
                    else None
                ),
                "scope_statement": (
                    output.analysis.scope_statement
                    if output.analysis is not None
                    else None
                ),
                "answer": None,
                "claims": [],
                "withheld_answer": (
                    output.analysis.short_answer
                    if output.analysis is not None
                    else None
                ),
                "withheld_claims": withheld_claims,
                "gaps": [asdict(gap) for gap in self._public_gaps(output)],
                "review_findings": (
                    [
                        {
                            **asdict(finding),
                            "claim_number": (
                                finding.claim_index + 1
                                if finding.claim_index is not None
                                and 0
                                <= finding.claim_index
                                < len(withheld_claims)
                                else None
                            ),
                        }
                        for finding in output.review.findings
                    ]
                    if output.review is not None
                    else []
                ),
            }

        return {
            "status": output.kind.value,
            "summary": output.summary,
            "conclusion_kind": output.analysis.conclusion_kind,
            "scope_statement": output.analysis.scope_statement,
            "answer": output.analysis.short_answer,
            "claims": self._serialize_claims(
                tuple(
                    output.analysis.claims[index]
                    for index in output.analysis.answer_claim_indices
                )
            ),
            "gaps": self._serialize_public_gaps(output),
            "review_findings": (
                [
                    {
                        "severity": finding.severity,
                        "code": finding.code,
                        "message": finding.message,
                        "claim_number": (
                            finding.claim_index + 1
                            if finding.claim_index is not None
                            else None
                        ),
                    }
                    for finding in output.review.findings
                ]
                if output.review is not None
                else []
            ),
        }

    def _serialize_claims(
        self,
        source_claims: tuple[Claim, ...],
        *,
        allow_invalid_locators: bool = False,
    ) -> list[dict[str, object]]:
        claims: list[dict[str, object]] = []
        for claim in source_claims:
            citations = []
            for locator in claim.locators:
                try:
                    source = self.corpus.document_metadata(locator.document_id)
                except KeyError:
                    if not allow_invalid_locators:
                        raise
                    citations.append(
                        {
                            "document_id": locator.document_id,
                            "title": (
                                f"Invalid evidence locator: {locator.document_id}"
                            ),
                            "publisher": None,
                            "document_date": None,
                            "url": None,
                            "page": locator.page,
                            "section": locator.section,
                            "timestamp": locator.timestamp,
                            "field": locator.field,
                            "invalid": True,
                        }
                    )
                    continue
                citations.append(
                    {
                        "document_id": locator.document_id,
                        "title": source["title"],
                        "publisher": source["publisher"],
                        "document_date": source["document_date"],
                        "url": source["url"] or source["attachment_url"],
                        "page": locator.page,
                        "section": locator.section,
                        "timestamp": locator.timestamp,
                        "field": locator.field,
                        "invalid": False,
                    }
                )
            claims.append(
                {
                    "text": claim.text,
                    "confidence": claim.confidence.value,
                    "does_not_establish": claim.does_not_establish,
                    "citations": citations,
                }
            )
        return claims

    @staticmethod
    def _public_gaps(output: RunDisposition) -> tuple[EvidenceGap, ...]:
        candidates = list(output.gaps)
        if output.analysis is not None:
            candidates.extend(output.analysis.gaps)
        if output.review is not None:
            candidates.extend(output.review.targeted_gaps)
        unique = {}
        for gap in candidates:
            key = gap.deciding_record.strip().lower()
            existing = unique.get(key)
            if existing is None:
                unique[key] = gap
                continue
            rationales = tuple(
                dict.fromkeys(
                    rationale
                    for rationale in (existing.rationale, gap.rationale)
                    if rationale
                )
            )
            unique[key] = replace(
                existing,
                likely_custodian=(
                    existing.likely_custodian or gap.likely_custodian
                ),
                search_before_request=tuple(
                    dict.fromkeys(
                        existing.search_before_request
                        + gap.search_before_request
                    )
                ),
                rationale="\n".join(rationales) if rationales else None,
                related_claim_indices=tuple(
                    dict.fromkeys(
                        existing.related_claim_indices
                        + gap.related_claim_indices
                    )
                ),
            )
        gaps = tuple(unique.values())
        if (
            output.kind != DispositionKind.ANSWER_READY
            or output.analysis is None
        ):
            return gaps
        return tuple(
            gap
            for gap in gaps
            if not gap.related_claim_indices
            or any(
                index in output.analysis.answer_claim_indices
                for index in gap.related_claim_indices
            )
        )

    @classmethod
    def _serialize_public_gaps(
        cls, output: RunDisposition
    ) -> list[dict[str, object]]:
        gaps = cls._public_gaps(output)
        if (
            output.kind != DispositionKind.ANSWER_READY
            or output.analysis is None
        ):
            return [asdict(gap) for gap in gaps]
        index_map = {
            original: replacement
            for replacement, original in enumerate(
                output.analysis.answer_claim_indices
            )
        }
        return [
            asdict(
                replace(
                    gap,
                    related_claim_indices=tuple(
                        index_map[index]
                        for index in gap.related_claim_indices
                        if index in index_map
                    ),
                )
            )
            for gap in gaps
        ]


class ChatRequestHandler(BaseHTTPRequestHandler):
    server_version = "MendoCaseChat/0.1"

    @property
    def chat_server(self) -> "ChatHTTPServer":
        return self.server  # type: ignore[return-value]

    def _headers(self, status: HTTPStatus, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()

    def _json(self, status: HTTPStatus, value: object) -> None:
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(value, sort_keys=True).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "case_id": self.chat_server.service.settings.case_id,
                    "runtime": provider_identity(
                        self.chat_server.service.settings.model_provider
                    ),
                },
            )
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/chat":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
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
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "Request body is empty or too large."},
            )
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or not isinstance(
                payload.get("question"), str
            ):
                raise PublicChatError("The request must contain a question string.")
            raw_history = payload.get("history", [])
            if not isinstance(raw_history, list) or not all(
                isinstance(message, dict) for message in raw_history
            ):
                raise PublicChatError(
                    "Conversation history must be an array of messages."
                )
            result = asyncio.run(
                self.chat_server.service.ask(
                    payload["question"],
                    tuple(raw_history),
                )
            )
            self._json(HTTPStatus.OK, result)
        except (json.JSONDecodeError, PublicChatError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            self.log_error(
                "Chat request failed: %s: %s",
                type(error).__name__,
                error,
            )
            traceback.print_exception(error)
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "The evidence workflow failed. No answer was published."},
            )

    def _serve_static(self, request_path: str) -> None:
        relative = request_path.lstrip("/") or "casebook.html"
        candidate = (self.chat_server.web_root / relative).resolve()
        try:
            candidate.relative_to(self.chat_server.web_root)
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
            + ("; charset=utf-8" if content_type and content_type.startswith("text/") else ""),
        )
        self.wfile.write(candidate.read_bytes())


class ChatHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        service: PublicChatService,
        web_root: Path,
    ) -> None:
        self.service = service
        self.web_root = web_root.resolve()
        super().__init__(address, ChatRequestHandler)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-chat")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--case-id")
    parser.add_argument("--provider", choices=("scripted", "ollama", "foundry"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    loaded = Settings.from_env(args.repo_root)
    return Settings(
        repo_root=loaded.repo_root,
        case_id=args.case_id or loaded.case_id,
        model_provider=args.provider or loaded.model_provider,
        checkpoint_root=loaded.checkpoint_root,
        run_root=loaded.run_root,
        research_queue_path=loaded.research_queue_path,
        max_iterations=loaded.max_iterations,
        max_research_rounds=0,
        enable_sensitive_telemetry=False,
    )


def main() -> None:
    args = _parser().parse_args()
    settings = _settings_from_args(args)
    server = ChatHTTPServer(
        (args.host, args.port),
        PublicChatService(settings),
        settings.repo_root / "web",
    )
    print(
        f"Mendocino case chat: http://{args.host}:{args.port}/casebook.html "
        f"({settings.model_provider})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
