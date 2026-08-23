"""Validate monitor contracts and compare normalized one-shot snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .models import MonitorObservation


@dataclass(frozen=True)
class SnapshotChange:
    repository_id: str
    kind: str
    canonical_url: str
    prior_state: str | None
    current_state: str | None
    changed_fingerprints: tuple[str, ...] = ()


class MonitorRegistry:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.root = self.repo_root / "monitors"
        self.schema_root = self.root / "schemas" / "v1"
        self.format_checker = FormatChecker()

    def _load(self, path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _validate(self, instance: dict, schema_name: str) -> None:
        schema = self._load(self.schema_root / schema_name)
        validator = Draft202012Validator(
            schema, format_checker=self.format_checker
        )
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            messages = "; ".join(
                f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
                for error in errors
            )
            raise ValueError(f"Invalid {schema_name}: {messages}")

    def load_and_validate(self) -> dict[str, dict]:
        registry = self._load(self.root / "registry.yaml")
        self._validate(registry, "registry.schema.yaml")
        definitions: dict[str, dict] = {}
        for item in registry["monitors"]:
            path = (self.root / item["definition"]).resolve()
            if self.root not in path.parents:
                raise ValueError(f"Monitor definition escapes monitor root: {path}")
            definition = self._load(path)
            self._validate(definition, "monitor.schema.yaml")
            if definition["id"] != item["id"]:
                raise ValueError(
                    f"Registry ID {item['id']} does not match {definition['id']}"
                )
            definitions[item["id"]] = definition
        return definitions

    def load_snapshot(self, path: Path, *, allow_fixture: bool = False) -> dict:
        snapshot = self._load(path)
        self._validate(snapshot, "snapshot.schema.yaml")
        if snapshot["fixture"] and not allow_fixture:
            raise ValueError(
                "Fixture snapshots require explicit allow_fixture=True"
            )
        return snapshot


def compare_snapshots(previous: dict, current: dict) -> tuple[SnapshotChange, ...]:
    if previous["monitor_id"] != current["monitor_id"]:
        raise ValueError("Snapshots belong to different monitors")
    old = {record["repository_id"]: record for record in previous["records"]}
    new = {record["repository_id"]: record for record in current["records"]}
    changes: list[SnapshotChange] = []
    for repository_id in sorted(set(old) | set(new)):
        prior = old.get(repository_id)
        latest = new.get(repository_id)
        if prior is None:
            changes.append(
                SnapshotChange(
                    repository_id=repository_id,
                    kind="new",
                    canonical_url=latest["canonical_url"],
                    prior_state=None,
                    current_state=latest["state"],
                )
            )
            continue
        if latest is None:
            changes.append(
                SnapshotChange(
                    repository_id=repository_id,
                    kind="missing_from_snapshot",
                    canonical_url=prior["canonical_url"],
                    prior_state=prior["state"],
                    current_state=None,
                )
            )
            continue
        fingerprint_names = sorted(
            key
            for key in set(prior["fingerprints"]) | set(latest["fingerprints"])
            if prior["fingerprints"].get(key) != latest["fingerprints"].get(key)
        )
        if prior["state"] != latest["state"] or fingerprint_names:
            changes.append(
                SnapshotChange(
                    repository_id=repository_id,
                    kind="changed",
                    canonical_url=latest["canonical_url"],
                    prior_state=prior["state"],
                    current_state=latest["state"],
                    changed_fingerprints=tuple(fingerprint_names),
                )
            )
    return tuple(changes)


def observation_from_snapshots(previous: dict, current: dict) -> MonitorObservation:
    changes = compare_snapshots(previous, current)
    descriptions = []
    urls = []
    for change in changes:
        detail = (
            f"{change.repository_id}:{change.kind}"
            f" ({change.prior_state or 'absent'} -> "
            f"{change.current_state or 'absent'})"
        )
        if change.changed_fingerprints:
            detail += f"; fingerprints={','.join(change.changed_fingerprints)}"
        descriptions.append(detail)
        if change.current_state == "downloadable":
            urls.append(change.canonical_url)
    summary = (
        f"Monitor detected {len(changes)} record changes: "
        + "; ".join(descriptions)
        if changes
        else "Monitor detected no record changes."
    )
    return MonitorObservation(
        monitor_id=current["monitor_id"],
        observed_at=current["observed_at"],
        summary=summary,
        candidate_urls=tuple(urls),
        prior_fingerprint=previous["snapshot"].get("cursor", {}).get(
            "collection_fingerprint"
        ),
        current_fingerprint=current["snapshot"].get("cursor", {}).get(
            "collection_fingerprint"
        ),
        change_count=len(changes),
    )
