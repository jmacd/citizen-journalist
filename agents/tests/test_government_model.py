from __future__ import annotations

from pathlib import Path

from mendo_agents.government_model import GovernmentModel


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_government_model_resolves_all_provenance_and_relationships() -> None:
    records = GovernmentModel(REPO_ROOT).load_and_validate()

    assert len(records) == 55
    assert "agency.mendocino-county" in records
    assert "agency.ca.coastal-commission" in records
    assert "office.mendocino-county.board-of-supervisors" in records
    assert "office.mendocino-county.planning-building-services" in records
    assert "proposal.project.community-emergency-delivery" in records
    proposal = records["proposal.project.community-emergency-delivery"]
    assert proposal.data["acceptance_status"] == "unknown"
    assert "must not" in proposal.data["assertions"][0]["limits"].lower()
