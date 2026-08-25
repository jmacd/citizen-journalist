"""Runtime configuration with local-first, cloud-ready defaults."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    case_id: str = "UM_2025-0004"
    model_provider: str = "scripted"
    checkpoint_root: Path | None = None
    run_root: Path | None = None
    research_queue_path: Path | None = None
    research_staging_root: Path | None = None
    max_iterations: int = 12
    max_research_rounds: int = 2
    enable_sensitive_telemetry: bool = False

    def __post_init__(self) -> None:
        root = self.repo_root.resolve()
        object.__setattr__(self, "repo_root", root)
        if self.checkpoint_root is None:
            object.__setattr__(
                self,
                "checkpoint_root",
                root / "captures" / "agent-runs" / "checkpoints",
            )
        if self.run_root is None:
            object.__setattr__(
                self,
                "run_root",
                root / "captures" / "agent-runs",
            )
        if self.research_queue_path is None:
            object.__setattr__(
                self,
                "research_queue_path",
                self.run_root / "research-queue.sqlite",
            )
        if self.research_staging_root is None:
            object.__setattr__(
                self,
                "research_staging_root",
                self.run_root / "research-staging",
            )

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> Settings:
        root = repo_root or Path(environ.get("MENDO_REPO_ROOT", Path.cwd()))
        return cls(
            repo_root=root,
            case_id=environ.get("MENDO_CASE_ID", "UM_2025-0004"),
            model_provider=environ.get("MENDO_MODEL_PROVIDER", "scripted"),
            checkpoint_root=(
                Path(environ["MENDO_CHECKPOINT_ROOT"])
                if environ.get("MENDO_CHECKPOINT_ROOT")
                else None
            ),
            run_root=(
                Path(environ["MENDO_RUN_ROOT"])
                if environ.get("MENDO_RUN_ROOT")
                else None
            ),
            research_queue_path=(
                Path(environ["MENDO_RESEARCH_QUEUE_PATH"])
                if environ.get("MENDO_RESEARCH_QUEUE_PATH")
                else None
            ),
            research_staging_root=(
                Path(environ["MENDO_RESEARCH_STAGING_ROOT"])
                if environ.get("MENDO_RESEARCH_STAGING_ROOT")
                else None
            ),
            max_iterations=int(environ.get("MENDO_MAX_ITERATIONS", "12")),
            max_research_rounds=int(environ.get("MENDO_MAX_RESEARCH_ROUNDS", "2")),
            enable_sensitive_telemetry=environ.get(
                "ENABLE_SENSITIVE_DATA", "false"
            ).lower()
            in {"1", "true", "yes"},
        )
