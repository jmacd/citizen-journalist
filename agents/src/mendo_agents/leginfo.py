"""Deterministic retrieval support for California Legislative Information."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

from .acquisition import PublicRecordFetcher
from .models import AcquisitionCandidate
from .repository import CorpusRepository
from .validation import validate_staged_record

LEGINFO_HOST = "leginfo.legislature.ca.gov"


class LeginfoIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class LeginfoRecord:
    target_id: str
    title: str
    law_code: str
    query: tuple[tuple[str, str], ...]
    expected_markers: tuple[str, ...]
    publisher: str = "California Legislative Information"
    document_date: str | None = None
    version: str = "current_consolidated_code"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{2,4}", self.law_code):
            raise ValueError(f"Invalid California code identifier: {self.law_code}")
        allowed = {
            "sectionNum",
            "division",
            "title",
            "part",
            "chapter",
            "article",
        }
        keys = [key for key, _ in self.query]
        if len(keys) != len(set(keys)) or any(key not in allowed for key in keys):
            raise ValueError("Invalid or duplicate LegInfo query field")
        if ("sectionNum" in keys) == any(
            key in keys for key in ("division", "title", "part", "chapter", "article")
        ):
            raise ValueError(
                "LegInfo record must identify either one section or one code range"
            )
        for _, value in self.query:
            if value and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*\.?", value):
                raise ValueError(f"Invalid LegInfo code location: {value}")

    @property
    def url(self) -> str:
        endpoint = (
            "codes_displaySection.xhtml"
            if any(key == "sectionNum" for key, _ in self.query)
            else "codes_displayText.xhtml"
        )
        parameters = (("lawCode", self.law_code), *self.query)
        return f"https://{LEGINFO_HOST}/faces/{endpoint}?{urlencode(parameters)}"


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def validate_leginfo_identity(content: bytes, record: LeginfoRecord) -> None:
    try:
        html = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LeginfoIdentityError("LegInfo response is not valid UTF-8") from error
    parser = _VisibleText()
    parser.feed(html)
    visible = " ".join(" ".join(parser.parts).split())
    missing = [marker for marker in record.expected_markers if marker not in visible]
    if missing:
        raise LeginfoIdentityError(
            f"LegInfo response omitted expected identity markers: {', '.join(missing)}"
        )


def stage_leginfo_records(
    records: tuple[LeginfoRecord, ...],
    staging_directory: Path,
    corpus: CorpusRepository,
    related_lead_ids: tuple[str, ...],
) -> Path:
    fetcher = PublicRecordFetcher({LEGINFO_HOST})
    candidates: list[dict[str, object]] = []
    staging_directory.mkdir(parents=True, exist_ok=True)
    for spec in records:
        acquisition = AcquisitionCandidate(
            target_id=spec.target_id,
            url=spec.url,
            issuing_body=spec.publisher,
            expected_title=spec.title,
            expected_date=spec.document_date,
            cited_by="deterministic-leginfo-resolver",
        )
        download = fetcher.fetch(acquisition, staging_directory)
        if download.status != "captured_staged" or not download.staging_path:
            raise LeginfoIdentityError(
                f"Could not stage {spec.target_id}: "
                f"{download.status}: {download.error or 'no error detail'}"
            )
        path = Path(download.staging_path)
        validate_leginfo_identity(path.read_bytes(), spec)
        validated = validate_staged_record(acquisition, path, corpus)
        if validated.duplicate_of is not None:
            continue
        candidates.append(
            {
                "id": spec.target_id,
                "title": spec.title,
                "publisher": spec.publisher,
                "document_date": spec.document_date,
                "source_url": download.final_url or spec.url,
                "retrieved_at": download.attempted_at,
                "status": "staged",
                "version": spec.version,
                "signature_status": "official_current_text",
                "mime_type": validated.mime_type,
                "bytes": validated.byte_count,
                "sha256": validated.sha256,
                "file_path": path.name,
                "establishes": [
                    "The current official text and amendment annotations "
                    "shown for the identified California Code provisions."
                ],
                "does_not_establish": [
                    "How the provisions apply to an unidentified transaction.",
                    "That authority belonging to one district type belongs to "
                    "another district type.",
                ],
                "related_lead_ids": list(related_lead_ids),
                "proposed_manifest": {
                    "id": spec.target_id.replace("-", "_"),
                    "title": spec.title,
                    "publisher": spec.publisher,
                    "document_date": spec.document_date,
                    "status": "captured",
                    "version": spec.version,
                },
            }
        )
    bundle = staging_directory / "review-bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "resolver": "california_legislative_information_v1",
                "records": [asdict(record) for record in records],
                "candidates": candidates,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle
