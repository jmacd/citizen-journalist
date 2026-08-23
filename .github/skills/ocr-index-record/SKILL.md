---
name: ocr-index-record
description: Extract page-addressable text from a digital or scanned public record, preserve the original, and add searchable text to the local case database.
---

# OCR and index a record

1. Preserve and hash the original before processing.
2. Attempt embedded-text extraction first. If pages are empty or unusable,
   render each page at 300 DPI and OCR it locally with Tesseract.
3. Keep page boundaries. Store locally generated OCR separately from the
   original and label it `locally_generated_tesseract`.
4. Hash the OCR output and register its path and hash beneath the document's
   `ocr` field in `manifest.yaml`.
5. Rebuild with `npm run build:case-db`.
6. Search distinctive names, identifiers, numbered clauses, and dates. Compare
   representative samples against page images.
7. Treat OCR as a finding aid. Quote the original image or PDF when exact
   wording controls.

For handwritten, tabular, mapped, or poor-quality pages, record low confidence
and require visual review. Never silently normalize names, section numbers, or
condition numbering.
