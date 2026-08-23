---
name: harvest-etrakit-case-record
description: Inventory Mendocino County eTRAKiT planning cases and anonymously retrieve current U_, UM_, and PC_ attachments with version-safe provenance.
---

# Harvest an eTRAKiT planning case

Use eTRAKiT as the case-centered planning index. Do not confuse it with the
meeting-centered GovAccess archive or the Cannabis-only Accela deployment.

1. Open the bookmarkable project record:
   `Search/project.aspx?activityNo=<record-number>`.
2. Record the case type, status, parent and child records, administrative dates,
   parcels, and linked `PC_` resolution records.
3. Enumerate current attachments with an anonymous `GET`:
   `attachmentUpload.aspx?Group=Project&ActivityNo=<record-number>&showCurrent=true&postbackid=nothing`.
4. Capture each attachment's displayed filename, key, case ID, MIME type, byte
   length, retrieval time, and direct `viewAttachment.aspx` URL.
5. Download through:
   `viewAttachment.aspx?Group=PROJECT&key=<key>&ActivityNo=<record-number>`.
6. Hash the original before extraction, OCR, conversion, or comparison.
7. Register native and rendered forms separately when both DOCX and PDF are
   available.
8. Follow linked predecessor, modification, and `PC_` records; attachment sets
   are uneven and may be stored only on one related record.
9. Compare condition-bearing records semantically. Never infer continuity from
   reused condition numbers.
10. Cross-check GovAccess meeting postings because later memoranda and revised
    drafts may be absent from the current eTRAKiT attachment inventory.
11. Treat `showCurrent=true` as a current public view, not a complete version
    history. Request database exports and audit metadata for deleted,
    superseded, inactive, staff-only, or replaced attachments.

Do not attempt upload actions. The attachment-index endpoint's filename is
misleading, but only anonymous read operations are part of this workflow.
