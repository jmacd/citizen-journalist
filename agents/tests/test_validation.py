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
