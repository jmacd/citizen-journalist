---
name: acquire-public-record
description: Locate, retrieve, verify, and register an official public record for a planning case without losing provenance or confusing an index entry with reviewed content.
---

# Acquire a public record

1. Identify the record precisely: issuing body, title, date, document ID, case
   number, version, signature status, and the source that cites it.
2. Search official repositories first. Then check another official agency that
   received the record, public meeting packets, CEQAnet, and public archives.
3. Do not evade authentication, anti-bot, or access controls. A known URL with a
   403 response is `identified_unretrieved`, not reviewed evidence.
4. Download the original into `captures/cases/<case-id>/`. Retain its original
   filename when practical.
5. Record byte count and SHA-256. Confirm MIME type and reject access-denied
   HTML saved under a PDF filename.
6. Add or update the source in `cases/<case-id>/manifest.yaml`.
7. Set a precise status such as `captured`, `identified_unretrieved`, `indexed`,
   `superseded`, or `draft`.
8. Rebuild the local database and verify the document appears once.

Report the official URL, retrieval time, identity, version relationship,
capture metadata, what the record establishes, and unresolved authenticity or
supersession issues. Never substitute an agenda label or staff summary for the
underlying document.
