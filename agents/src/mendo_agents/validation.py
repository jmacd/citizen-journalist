"""Deterministic validation for staged public records and citations."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from pypdf import PdfReader

from .models import AcquisitionCandidate, ValidatedRecord
from .repository import CorpusRepository


class RecordValidationError(ValueError):
    pass


def _mime_type(path: Path) -> str:
    prefix = path.read_bytes()[:512]
    if prefix.startswith(b"%PDF-"):
        return "application/pdf"
    lowered = prefix.lstrip().lower()
    if lowered.startswith((b"<!doctype html", b"<html")):
        return "text/html"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _ocr_page_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(text.split("\f"))


def validate_staged_record(
    candidate: AcquisitionCandidate,
    path: Path,
    corpus: CorpusRepository,
    ocr_path: Path | None = None,
) -> ValidatedRecord:
    resolved = path.resolve()
    if not resolved.is_file():
        raise RecordValidationError(f"Staged record does not exist: {resolved}")
    content = resolved.read_bytes()
    mime_type = _mime_type(resolved)
    if mime_type == "text/html" and resolved.suffix.lower() == ".pdf":
        raise RecordValidationError("Access-denied or HTML response saved as a PDF")
    if mime_type != "application/pdf":
        raise RecordValidationError(f"Unsupported staged MIME type: {mime_type}")

    digest = hashlib.sha256(content).hexdigest()
    reader = PdfReader(resolved)
    page_count = len(reader.pages)
    warnings: list[str] = []
    ocr_pages = None
    if ocr_path is not None:
        if not ocr_path.is_file():
            raise RecordValidationError(f"OCR file does not exist: {ocr_path}")
        ocr_pages = _ocr_page_count(ocr_path)
        if ocr_pages != page_count:
            raise RecordValidationError(
                f"OCR has {ocr_pages} segments for a {page_count}-page PDF"
            )
        warnings.append("OCR is a locally generated finding aid")

    return ValidatedRecord(
        candidate=candidate,
        staging_path=str(resolved),
        mime_type=mime_type,
        byte_count=len(content),
        sha256=digest,
        duplicate_of=corpus.document_by_hash(digest),
        page_count=page_count,
        ocr_page_count=ocr_pages,
        warnings=tuple(warnings),
    )


def verify_staged_record_unchanged(record: ValidatedRecord) -> None:
    path = Path(record.staging_path)
    if not path.is_file():
        raise RecordValidationError(
            f"Approved staged record no longer exists: {record.staging_path}"
        )
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if len(content) != record.byte_count or digest != record.sha256:
        raise RecordValidationError(
            "Staged record bytes changed after Archivist validation: "
            f"{record.candidate.target_id}"
        )
