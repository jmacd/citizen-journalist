from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from mendo_agents.monitoring import (
    MonitorRegistry,
    compare_snapshots,
    observation_from_snapshots,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_registry_and_fixtures_validate() -> None:
    registry = MonitorRegistry(REPO_ROOT)
    definitions = registry.load_and_validate()

    assert len(definitions) == 9
    assert "planning-commission-govaccess" in definitions
    fixture = registry.load_snapshot(
        REPO_ROOT / "monitors/fixtures/govaccess-snapshot.yaml",
        allow_fixture=True,
    )
    assert fixture["monitor_id"] == "planning-commission-govaccess"


def test_fixture_snapshot_requires_explicit_permission() -> None:
    registry = MonitorRegistry(REPO_ROOT)
    with pytest.raises(ValueError, match="explicit"):
        registry.load_snapshot(
            REPO_ROOT / "monitors/fixtures/govaccess-snapshot.yaml"
        )


def test_snapshot_comparison_routes_new_downloadable_record() -> None:
    snapshot = yaml.safe_load(
        (REPO_ROOT / "monitors/fixtures/govaccess-snapshot.yaml").read_text(
            encoding="utf-8"
        )
    )
    current = deepcopy(snapshot)
    current["observed_at"] = "2026-08-22T12:00:00Z"
    current["records"].append(
        {
            "repository_id": "80000",
            "canonical_url": (
                "https://www.mendocinocounty.gov/home/showpublisheddocument/"
                "80000/639230000000000000"
            ),
            "title": "New packet",
            "identifiers": {"govaccess_document_id": "80000"},
            "fingerprints": {"identity": "80000"},
            "state": "downloadable",
        }
    )

    changes = compare_snapshots(snapshot, current)
    observation = observation_from_snapshots(snapshot, current)

    assert changes[-1].kind == "new"
    assert "80000:new" in observation.summary
    assert observation.candidate_urls == (
        current["records"][-1]["canonical_url"],
    )
    assert observation.change_count == 1
