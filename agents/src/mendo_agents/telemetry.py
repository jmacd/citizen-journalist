"""OpenTelemetry configuration and non-sensitive workflow metrics."""

from __future__ import annotations

from dataclasses import dataclass

from agent_framework.observability import (
    configure_otel_providers,
    get_meter,
    get_tracer,
)


@dataclass(frozen=True)
class Telemetry:
    runs: object
    approvals: object
    outcomes: object
    tracer: object

    def run_started(self, case_id: str, input_kind: str) -> None:
        self.runs.add(1, {"case_id": case_id, "input_kind": input_kind})

    def approval_requested(self, kind: str) -> None:
        self.approvals.add(1, {"kind": kind})

    def run_completed(self, disposition: str) -> None:
        self.outcomes.add(1, {"disposition": disposition})


def configure_telemetry(enable_sensitive_data: bool = False) -> Telemetry:
    configure_otel_providers(enable_sensitive_data=enable_sensitive_data)
    meter = get_meter("mendo_agents")
    return Telemetry(
        runs=meter.create_counter(
            "mendo.agent.runs",
            description="Evidence workflow runs started",
        ),
        approvals=meter.create_counter(
            "mendo.agent.approvals",
            description="CIO approval requests emitted",
        ),
        outcomes=meter.create_counter(
            "mendo.agent.outcomes",
            description="Evidence workflow terminal dispositions",
        ),
        tracer=get_tracer("mendo_agents"),
    )
