"""Role and approval policy loading and invariant checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


CANONICAL_WRITE_CAPABILITIES = {
    "write_case_manifest",
    "write_government_model",
    "send_external_request",
}


@dataclass(frozen=True)
class RolePolicy:
    id: str
    name: str
    instructions: str
    allowed_tools: tuple[str, ...]
    prohibited_actions: tuple[str, ...]


@dataclass(frozen=True)
class SocietyPolicy:
    schema_version: int
    roles: dict[str, RolePolicy]
    approval_required: tuple[str, ...]


def load_society_policy(path: Path) -> SocietyPolicy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    roles = {
        role["id"]: RolePolicy(
            id=role["id"],
            name=role["name"],
            instructions=role["instructions"],
            allowed_tools=tuple(role.get("allowed_tools", [])),
            prohibited_actions=tuple(role.get("prohibited_actions", [])),
        )
        for role in raw["roles"]
    }
    policy = SocietyPolicy(
        schema_version=raw["schema_version"],
        roles=roles,
        approval_required=tuple(raw["approval_policy"]["required_for"]),
    )
    validate_society_policy(policy)
    return policy


def validate_society_policy(policy: SocietyPolicy) -> None:
    expected_roles = {
        "case_worker",
        "scout",
        "archivist",
        "analyst",
        "skeptic",
        "acquisition_engineer",
    }
    missing = expected_roles - set(policy.roles)
    if missing:
        raise ValueError(f"Missing active role policies: {sorted(missing)}")
    for role in policy.roles.values():
        forbidden = CANONICAL_WRITE_CAPABILITIES.intersection(role.allowed_tools)
        if forbidden:
            raise ValueError(
                f"Role {role.id} has forbidden direct capabilities: {sorted(forbidden)}"
            )
    required_gates = {
        "document_registration",
        "knowledge_promotion",
        "supersession",
        "publication",
        "external_communication",
    }
    missing_gates = required_gates - set(policy.approval_required)
    if missing_gates:
        raise ValueError(f"Missing CIO approval gates: {sorted(missing_gates)}")
