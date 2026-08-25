"""Local CLI for starting, approving, and resuming evidence workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent_framework import FileCheckpointStorage

from .acquisition import PublicRecordFetcher
from .config import Settings
from .journal import RunJournal, _json_default
from .models import (
    ApprovalBundle,
    ApprovalDecision,
    CaseQuestion,
    MonitorObservation,
    RunDisposition,
)
from .monitoring import MonitorRegistry, observation_from_snapshots
from .policy import load_society_policy
from .providers import create_reasoner
from .repository import CorpusRepository
from .research_dispatch import (
    FoundryWebSearchScout,
    ResearchDirectiveStore,
    ResearchDispatcher,
)
from .skills import load_skills
from .telemetry import configure_telemetry
from .workflow import build_evidence_workflow


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mendo-agents")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--case-id")
    parser.add_argument(
        "--provider", choices=("scripted", "ollama", "foundry")
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--auto-approve", action="store_true")

    observe = subparsers.add_parser("observe")
    observe.add_argument("--monitor-id", required=True)
    observe.add_argument("--summary", required=True)
    observe.add_argument("--url", action="append", default=[])
    observe.add_argument("--auto-approve", action="store_true")

    resume = subparsers.add_parser("resume")
    resume.add_argument("checkpoint_id")
    resume.add_argument("--auto-approve", action="store_true")

    tick = subparsers.add_parser("monitor-tick")
    tick.add_argument("--previous", type=Path, required=True)
    tick.add_argument("--current", type=Path, required=True)
    tick.add_argument(
        "--allow-fixtures",
        action="store_true",
        help="Allow fixture snapshots intended only for tests and demonstrations",
    )
    tick.add_argument("--auto-approve", action="store_true")

    subparsers.add_parser("checkpoints")

    research = subparsers.add_parser("research")
    research_commands = research.add_subparsers(
        dest="research_command", required=True
    )
    research_commands.add_parser("list")
    research_show = research_commands.add_parser("show")
    research_show.add_argument("directive_id")
    research_prepare = research_commands.add_parser("prepare")
    research_prepare.add_argument("--title", required=True)
    research_prepare.add_argument("--brief", required=True)
    research_prepare.add_argument("--lead", action="append", required=True)
    research_prepare.add_argument(
        "--allow-host", action="append", required=True
    )
    research_approve = research_commands.add_parser("approve")
    research_approve.add_argument("directive_id")
    research_approve.add_argument("--actor", default="cio")
    research_dispatch = research_commands.add_parser("dispatch")
    research_dispatch.add_argument("directive_id")
    research_runs = research_commands.add_parser("runs")
    research_runs.add_argument("directive_id", nargs="?")
    return parser


def _print_approval(bundle: ApprovalBundle) -> ApprovalDecision:
    print("\nCIO approval required:")
    for request in bundle.requests:
        print(f"- [{request.kind.value}] {request.summary}")
        if request.evidence_ids:
            print(f"  evidence: {', '.join(request.evidence_ids)}")
        if request.diff:
            print(request.diff)
    answer = input("Approve all displayed actions? [y/N] ").strip().lower()
    if answer in {"y", "yes"}:
        return ApprovalDecision(approved=True)
    feedback = input("Reason or revision guidance: ").strip()
    return ApprovalDecision(approved=False, feedback=feedback)


async def _run(args: argparse.Namespace) -> int:
    settings = Settings.from_env(args.repo_root)
    effective_case_id = args.case_id or settings.case_id
    effective_provider = args.provider or settings.model_provider
    settings = Settings(
        repo_root=settings.repo_root,
        case_id=effective_case_id,
        model_provider=effective_provider,
        checkpoint_root=settings.checkpoint_root,
        run_root=settings.run_root,
        research_queue_path=settings.research_queue_path,
        research_staging_root=settings.research_staging_root,
        max_iterations=settings.max_iterations,
        max_research_rounds=settings.max_research_rounds,
        enable_sensitive_telemetry=settings.enable_sensitive_telemetry,
    )
    args.case_id = effective_case_id
    args.provider = effective_provider

    if args.command == "research":
        store = ResearchDirectiveStore(settings.research_queue_path)
        if args.research_command == "list":
            value = [asdict(item) for item in store.list()]
        elif args.research_command == "show":
            value = asdict(store.get(args.directive_id))
        elif args.research_command == "prepare":
            value = asdict(
                store.create(
                    settings.case_id,
                    args.title,
                    args.brief,
                    tuple(args.lead),
                    tuple(args.allow_host),
                )
            )
        elif args.research_command == "approve":
            directive = store.get(args.directive_id)
            print(json.dumps(asdict(directive), indent=2, sort_keys=True))
            answer = input(
                "Approve this public web-search directive and host list? [y/N] "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                raise RuntimeError("Research directive approval declined")
            value = asdict(store.approve(args.directive_id, args.actor))
        elif args.research_command == "dispatch":
            if effective_provider != "foundry":
                raise RuntimeError(
                    "Web research dispatch currently requires --provider foundry"
                )
            value = ResearchDispatcher(
                store,
                FoundryWebSearchScout(),
                CorpusRepository(settings.repo_root, settings.case_id),
                settings.research_staging_root,
            ).dispatch(args.directive_id)
        else:
            value = store.runs(args.directive_id)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0

    checkpoint_path = settings.checkpoint_root / settings.case_id
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    storage = FileCheckpointStorage(storage_path=checkpoint_path)
    corpus = CorpusRepository(settings.repo_root, args.case_id)
    policy = load_society_policy(
        settings.repo_root / "agents" / "organization" / "society.yaml"
    )
    skills = load_skills(settings.repo_root)
    workflow = build_evidence_workflow(
        corpus,
        policy,
        skills,
        create_reasoner(args.provider),
        storage,
        fetcher=PublicRecordFetcher(
            {
                "www.mendocinocounty.gov",
                "mendocinocounty.gov",
                "mccsd.com",
                "www.mccsd.com",
                "www.mendocinousd.org",
                "mendocinousd.org",
                "www.mendolafco.org",
                "mendolafco.org",
                "documents.coastal.ca.gov",
                "ceqanet.opr.ca.gov",
                "www.waterboards.ca.gov",
                "waterboards.ca.gov",
                "library.municode.com",
            }
        ),
        staging_root=settings.run_root,
        max_iterations=settings.max_iterations,
        max_research_rounds=settings.max_research_rounds,
    )
    telemetry = configure_telemetry(settings.enable_sensitive_telemetry)

    if args.command == "checkpoints":
        checkpoints = await storage.list_checkpoints(workflow_name=workflow.name)
        for checkpoint in checkpoints:
            print(
                json.dumps(
                    {
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "timestamp": checkpoint.timestamp,
                        "iteration_count": checkpoint.iteration_count,
                    },
                    sort_keys=True,
                )
            )
        return 0

    run_id = str(uuid4())
    journal = RunJournal(settings.run_root, run_id)
    journal.write_manifest(
        {
            "run_id": run_id,
            "started_at": datetime.now(UTC).isoformat(),
            "case_id": args.case_id,
            "provider": args.provider,
            "workflow_version": 1,
            "policy_version": policy.schema_version,
            "skill_hashes": {name: skill.sha256 for name, skill in skills.items()},
            "sensitive_telemetry": settings.enable_sensitive_telemetry,
        }
    )

    if args.command == "ask":
        initial = CaseQuestion(case_id=args.case_id, question=args.question)
        stream = workflow.run(initial, stream=True)
    elif args.command == "observe":
        initial = MonitorObservation(
            monitor_id=args.monitor_id,
            observed_at=datetime.now(UTC).isoformat(),
            summary=args.summary,
            candidate_urls=tuple(args.url),
        )
        stream = workflow.run(initial, stream=True)
    elif args.command == "monitor-tick":
        registry = MonitorRegistry(settings.repo_root)
        definitions = registry.load_and_validate()
        previous = registry.load_snapshot(
            args.previous, allow_fixture=args.allow_fixtures
        )
        current = registry.load_snapshot(
            args.current, allow_fixture=args.allow_fixtures
        )
        if current["monitor_id"] not in definitions:
            raise ValueError(
                f"Snapshot uses unregistered monitor: {current['monitor_id']}"
            )
        initial = observation_from_snapshots(previous, current)
        stream = workflow.run(initial, stream=True)
    else:
        initial = None
        stream = workflow.run(checkpoint_id=args.checkpoint_id, stream=True)

    journal.append("input", initial or {"checkpoint_id": args.checkpoint_id})
    telemetry.run_started(
        args.case_id,
        type(initial).__name__ if initial is not None else "CheckpointResume",
    )
    auto_approve = getattr(args, "auto_approve", False)
    while True:
        responses: dict[str, ApprovalDecision] = {}
        output: RunDisposition | None = None
        async for event in stream:
            journal.append(f"workflow.{event.type}", event.data)
            if event.type == "request_info":
                if not isinstance(event.data, ApprovalBundle):
                    raise RuntimeError(
                        f"Unexpected approval request type: {type(event.data)}"
                    )
                for request in event.data.requests:
                    telemetry.approval_requested(request.kind.value)
                decision = (
                    ApprovalDecision(approved=True)
                    if auto_approve
                    else _print_approval(event.data)
                )
                journal.append("cio.decision", decision)
                responses[event.request_id] = decision
            elif event.type == "output":
                output = event.data
        if output is not None:
            telemetry.run_completed(output.kind.value)
            print(
                json.dumps(
                    output, default=_json_default, indent=2, sort_keys=True
                )
            )
            return (
                0
                if output.kind.value in {"answer_ready", "no_change"}
                else 2
            )
        if responses:
            stream = workflow.run(stream=True, responses=responses)
            continue
        raise RuntimeError("Workflow ended without output or approval request")


def main() -> None:
    raise SystemExit(asyncio.run(_run(_parser().parse_args())))


if __name__ == "__main__":
    main()
