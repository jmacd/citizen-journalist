from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from mendo_agents.models import AcquisitionCandidate
from mendo_agents.repository import CorpusRepository
from mendo_agents.validation import (
    RecordValidationError,
    validate_staged_record,
    verify_staged_record_unchanged,
)


def test_rejects_html_disguised_as_pdf(fixture_repo: Path, tmp_path: Path) -> None:
    path = tmp_path / "blocked.pdf"
    path.write_text("<html><title>Access denied</title></html>", encoding="utf-8")
    candidate = AcquisitionCandidate(
        target_id="blocked",
        url="https://example.gov/blocked.pdf",
        issuing_body="Example Agency",
        expected_title="Blocked record",
    )

    with pytest.raises(RecordValidationError, match="saved as a PDF"):
        validate_staged_record(
            candidate, path, CorpusRepository(fixture_repo, "TEST-CASE")
        )


def test_accepts_official_xhtml_snapshot(
    fixture_repo: Path, tmp_path: Path
) -> None:
    path = tmp_path / "codes_displaySection.xhtml"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<!DOCTYPE html><html><head><title>California Code, GOV 56133</title>"
        "</head><body><main>Current statutory text</main></body></html>",
        encoding="utf-8",
    )
    candidate = AcquisitionCandidate(
        target_id="gov-56133",
        url="https://leginfo.legislature.ca.gov/codes_displaySection.xhtml",
        issuing_body="California Legislative Information",
        expected_title="Government Code section 56133",
    )

    record = validate_staged_record(
        candidate, path, CorpusRepository(fixture_repo, "TEST-CASE")
    )

    assert record.mime_type == "text/html"
    assert record.page_count is None
    assert record.warnings == ("HTML snapshot has no stable page locators",)


def test_rejects_access_denied_xhtml(
    fixture_repo: Path, tmp_path: Path
) -> None:
    path = tmp_path / "blocked.xhtml"
    path.write_text(
        "<html><head><title>Access Denied</title></head><body></body></html>",
        encoding="utf-8",
    )
    candidate = AcquisitionCandidate(
        target_id="blocked",
        url="https://example.gov/blocked.xhtml",
        issuing_body="Example Agency",
        expected_title="Blocked record",
    )

    with pytest.raises(RecordValidationError, match="Access-denied HTML"):
        validate_staged_record(
            candidate, path, CorpusRepository(fixture_repo, "TEST-CASE")
        )


def test_approved_staged_bytes_are_rechecked(
    fixture_repo: Path, tmp_path: Path
) -> None:
    path = tmp_path / "record.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)
    candidate = AcquisitionCandidate(
        target_id="record",
        url="https://example.gov/record.pdf",
        issuing_body="Example",
        expected_title="Record",
    )
    record = validate_staged_record(
        candidate, path, CorpusRepository(fixture_repo, "TEST-CASE")
    )
    path.write_bytes(path.read_bytes() + b"changed")

    with pytest.raises(RecordValidationError, match="changed"):
        verify_staged_record_unchanged(record)
