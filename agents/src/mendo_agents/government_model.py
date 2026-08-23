"""Validation and read access for the cross-case institutional model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


MODEL_FILES = (
    "agencies.yaml",
    "offices.yaml",
    "jurisdictions.yaml",
    "legal-instruments.yaml",
    "boundaries.yaml",
    "procedures.yaml",
    "relationships.yaml",
    "proposals.yaml",
)


@dataclass(frozen=True)
class GovernmentRecord:
    entity_type: str
    id: str
    data: dict


class GovernmentModel:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.model_root = self.repo_root / "government-model"
        self.schema = yaml.safe_load(
            (self.model_root / "schema.yaml").read_text(encoding="utf-8")
        )
        self.records: dict[str, GovernmentRecord] = {}

    def load_and_validate(self) -> dict[str, GovernmentRecord]:
        evidence_statuses = set(self.schema["evidence_status"])
        acceptance_statuses = set(self.schema["acceptance_status"])
        instrument_statuses = set(self.schema["instrument_status"])
        boundary_kinds = set(self.schema["boundary_kind"])
        relationship_kinds = set(self.schema["relationship_kind"])
        source_ids_by_case: dict[str, set[str]] = {}
        records: dict[str, GovernmentRecord] = {}
        assertion_ids: set[str] = set()
        id_pattern = re.compile(self.schema["common_record"]["id_pattern"])
        assertion_required = set(
            self.schema["common_record"]["assertions"]["required_fields"]
        )

        for filename in MODEL_FILES:
            document = yaml.safe_load(
                (self.model_root / filename).read_text(encoding="utf-8")
            )
            entity_type = document["entity_type"]
            required = set(
                self.schema["entity_shapes"][entity_type]["required_fields"]
            )
            for data in document["records"]:
                missing = required - set(data)
                if missing:
                    raise ValueError(
                        f"{filename}:{data.get('id')} missing {sorted(missing)}"
                    )
                if data["id"] in records:
                    raise ValueError(f"Duplicate government record ID: {data['id']}")
                if not id_pattern.fullmatch(data["id"]):
                    raise ValueError(f"Invalid government record ID: {data['id']}")
                if not isinstance(data["assertions"], list) or not data["assertions"]:
                    raise ValueError(f"{data['id']} must have at least one assertion")
                if entity_type == "boundary" and data["kind"] not in boundary_kinds:
                    raise ValueError(f"Invalid boundary kind: {data['kind']}")
                if (
                    entity_type == "relationship"
                    and data["kind"] not in relationship_kinds
                ):
                    raise ValueError(f"Invalid relationship kind: {data['kind']}")
                if (
                    entity_type == "legal_instrument"
                    and data["instrument_status"] not in instrument_statuses
                ):
                    raise ValueError(
                        f"Invalid instrument status: {data['instrument_status']}"
                    )
                for assertion in data["assertions"]:
                    missing_assertion_fields = assertion_required - set(assertion)
                    if missing_assertion_fields:
                        raise ValueError(
                            f"{data['id']} assertion missing "
                            f"{sorted(missing_assertion_fields)}"
                        )
                    assertion_id = assertion["id"]
                    if assertion_id in assertion_ids:
                        raise ValueError(f"Duplicate assertion ID: {assertion_id}")
                    if not id_pattern.fullmatch(assertion_id):
                        raise ValueError(f"Invalid assertion ID: {assertion_id}")
                    assertion_ids.add(assertion_id)
                    if assertion["evidence_status"] not in evidence_statuses:
                        raise ValueError(
                            f"Invalid evidence status: {assertion['evidence_status']}"
                        )
                    if assertion["acceptance_status"] not in acceptance_statuses:
                        raise ValueError(
                            "Invalid acceptance status: "
                            f"{assertion['acceptance_status']}"
                        )
                    if not assertion.get("limits", "").strip():
                        raise ValueError(f"Assertion {assertion_id} has no limits")
                    if not assertion.get("statement", "").strip():
                        raise ValueError(f"Assertion {assertion_id} has no statement")
                    if not assertion.get("source_ids"):
                        raise ValueError(
                            f"Assertion {assertion_id} has no source provenance"
                        )
                    if assertion["evidence_status"] == "unresolved":
                        resolution_need = (
                            assertion.get("missing_record", "").strip()
                            or assertion.get("open_question", "").strip()
                        )
                        if not resolution_need:
                            raise ValueError(
                                f"Unresolved assertion {assertion_id} does not "
                                "identify the missing record or question"
                            )
                    case_id = assertion["case_id"]
                    source_ids = source_ids_by_case.get(case_id)
                    if source_ids is None:
                        source_ids = self._manifest_source_ids(case_id)
                        source_ids_by_case[case_id] = source_ids
                    unknown = set(assertion["source_ids"]) - source_ids
                    if unknown:
                        raise ValueError(
                            f"Assertion {assertion_id} has unknown sources: "
                            f"{sorted(unknown)}"
                        )
                records[data["id"]] = GovernmentRecord(
                    entity_type=entity_type,
                    id=data["id"],
                    data=data,
                )

        self._validate_cross_references(records)
        self.records = records
        return records

    def _manifest_source_ids(self, case_id: str) -> set[str]:
        manifest_path = self.repo_root / "cases" / case_id / "manifest.yaml"
        if not manifest_path.is_file():
            raise ValueError(f"Government model refers to unknown case: {case_id}")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        return {source["id"] for source in manifest["sources"]}

    @staticmethod
    def _validate_cross_references(records: dict[str, GovernmentRecord]) -> None:
        references = {
            "parent_agency_id",
            "holder_ids",
            "issuing_actor_ids",
            "authority_actor_ids",
            "actor_ids",
            "proponent_ids",
        }
        for record in records.values():
            for field in references:
                values = record.data.get(field)
                if values is None:
                    continue
                values = [values] if isinstance(values, str) else values
                unknown = set(values) - set(records)
                if unknown:
                    raise ValueError(
                        f"{record.id}.{field} has unknown IDs: {sorted(unknown)}"
                    )
            if record.entity_type == "relationship":
                for field in ("from_id", "to_id"):
                    if record.data[field] not in records:
                        raise ValueError(
                            f"{record.id}.{field} has unknown ID: {record.data[field]}"
                        )
            if record.entity_type == "office":
                parent = records[record.data["parent_agency_id"]]
                if parent.entity_type != "agency":
                    raise ValueError(
                        f"{record.id}.parent_agency_id must refer to an agency"
                    )
