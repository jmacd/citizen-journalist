from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from mendo_agents.acquisition_engineering import (
    AcquisitionEngineeringError,
    AcquisitionEngineeringStore,
    FoundryAcquisitionEngineer,
    ResearchRecoveryOrchestrator,
)
from mendo_agents.models import AcquisitionDiagnosis, EvidenceGap
from mendo_agents.research_dispatch import ResearchDirectiveStore
from mendo_agents.research_queue import ResearchQueue


def failed_run(tmp_path: Path) -> tuple[Path, int, str]:
    path = tmp_path / "research-queue.sqlite"
    queue = ResearchQueue(path)
    lead = queue.enqueue(
        "CASE-1",
        "Find the official record",
        (
            EvidenceGap(
                description="The direct record is missing.",
                deciding_record="Final official record",
            ),
        ),
        origin_type="foundry_public_chat",
        initiating_actor="cio",
    )[0]
    directives = ResearchDirectiveStore(path)
    directive = directives.create(
        "CASE-1",
        "Find final record",
        "Locate the final official record.",
        (lead.id,),
        ("records.example.gov",),
    )
    directives.approve(directive.id, "cio")
    run_id = directives.start(directive.id)
    directives.fail(
        directive.id,
        run_id,
        RuntimeError("Foundry cited an unapproved host: www.records.example.gov"),
    )
    return path, run_id, directive.id


def test_recovery_orchestrator_records_one_typed_diagnosis(
    tmp_path: Path,
) -> None:
    path, run_id, directive_id = failed_run(tmp_path)
    store = AcquisitionEngineeringStore(path)

    class Diagnoser:
        calls = 0

        def diagnose(self, failure):
            self.calls += 1
            return AcquisitionDiagnosis(
                id="diagnosis-1",
                run_id=failure.run_id,
                directive_id=failure.directive_id,
                failure_kind="host_allowlist",
                summary="Official host uses its www alias.",
                root_cause="The exact redirected host was not approved.",
                repair_kind="allowlist_revision",
                code_change_required=False,
                proposed_changes=(
                    {
                        "type": "allow_host",
                        "path": "",
                        "description": "Ask the CIO to approve the official alias.",
                    },
                ),
                safety_constraints=("Retain exact-host enforcement.",),
                citations=(),
                provider="scripted",
                model="fixture",
                status="diagnosis_pending_review",
                created_at="2026-08-26T03:00:00+00:00",
            )

    diagnoser = Diagnoser()
    orchestrator = ResearchRecoveryOrchestrator(store, diagnoser)
    first = orchestrator.diagnose(run_id)
    second = orchestrator.diagnose(run_id)

    assert first == second
    assert first.directive_id == directive_id
    assert first.failure_kind == "host_allowlist"
    assert diagnoser.calls == 1
    failure = store.failure(run_id)
    assert failure.error_type == "RuntimeError"
    assert failure.directive_snapshot_status == "captured_at_dispatch"
    assert failure.allowed_hosts == ("records.example.gov",)


def test_failure_loader_rejects_nonterminal_run(tmp_path: Path) -> None:
    path, run_id, _ = failed_run(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE research_dispatch_runs SET status = 'running' WHERE id = ?",
            (run_id,),
        )

    with pytest.raises(
        AcquisitionEngineeringError, match="not a terminal failure"
    ):
        AcquisitionEngineeringStore(path).failure(run_id)


def test_foundry_diagnosis_rejects_code_outside_adapter_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.test/project")
    monkeypatch.setenv("FOUNDRY_MODEL", "test-model")
    monkeypatch.setenv("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "true")
    path, run_id, _ = failed_run(tmp_path)
    failure = AcquisitionEngineeringStore(path).failure(run_id)
    raw = json.dumps(
        {
            "failure_kind": "identity_validation",
            "summary": "Validation rejected the record.",
            "root_cause": "A repository-specific envelope needs parsing.",
            "repair_kind": "validation_change",
            "code_change_required": True,
            "proposed_changes": [
                {
                    "type": "modify",
                    "path": "agents/src/mendo_agents/validation.py",
                    "description": "Relax global validation.",
                }
            ],
            "safety_constraints": ["Preserve MIME checks."],
            "citations": [],
        }
    )

    with pytest.raises(
        AcquisitionEngineeringError, match="outside the isolated adapter scope"
    ):
        FoundryAcquisitionEngineer()._parse(failure, raw, ())


def test_foundry_diagnosis_accepts_new_isolated_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.test/project")
    monkeypatch.setenv("FOUNDRY_MODEL", "test-model")
    monkeypatch.setenv("MENDO_FOUNDRY_WEB_SEARCH_ENABLED", "true")
    path, run_id, _ = failed_run(tmp_path)
    failure = AcquisitionEngineeringStore(path).failure(run_id)
    raw = json.dumps(
        {
            "failure_kind": "repository_access",
            "summary": "The repository needs a deterministic resolver.",
            "root_cause": "Search does not expose stable direct URLs.",
            "repair_kind": "deterministic_adapter",
            "code_change_required": True,
            "proposed_changes": [
                {
                    "type": "add",
                    "path": (
                        "agents/src/mendo_agents/repository_adapters/"
                        "example_records.py"
                    ),
                    "description": "Add a structured official-record resolver.",
                },
                {
                    "type": "add",
                    "path": (
                        "agents/tests/repository_adapters/"
                        "test_example_records.py"
                    ),
                    "description": "Test URL construction and identity checks.",
                },
            ],
            "safety_constraints": ["Preserve exact-host enforcement."],
            "citations": [],
        }
    )

    diagnosis = FoundryAcquisitionEngineer()._parse(failure, raw, ())
    assert diagnosis.code_change_required
    assert diagnosis.repair_kind == "deterministic_adapter"
