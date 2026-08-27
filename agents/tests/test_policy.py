from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mendo_agents.policy import load_society_policy
from mendo_agents.skills import load_skills


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_society_policy_has_balanced_gates_and_no_canonical_write_tools() -> None:
    policy = load_society_policy(REPO_ROOT / "agents/organization/society.yaml")

    assert set(policy.roles) == {
        "case_worker",
        "scout",
        "archivist",
        "analyst",
        "skeptic",
        "acquisition_engineer",
    }
    assert "external_communication" in policy.approval_required
    assert all(
        "write_case_manifest" not in role.allowed_tools
        for role in policy.roles.values()
    )


def test_policy_rejects_direct_canonical_capability(tmp_path: Path) -> None:
    raw = yaml.safe_load(
        (REPO_ROOT / "agents/organization/society.yaml").read_text(
            encoding="utf-8"
        )
    )
    raw["roles"][0]["allowed_tools"].append("write_case_manifest")
    path = tmp_path / "society.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="forbidden direct capabilities"):
        load_society_policy(path)


def test_skill_loader_records_content_hash(fixture_repo: Path) -> None:
    skills = load_skills(fixture_repo)

    assert set(skills) == {"answer-case-question"}
    assert len(skills["answer-case-question"].sha256) == 64
