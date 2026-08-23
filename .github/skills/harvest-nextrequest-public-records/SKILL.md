---
name: harvest-nextrequest-public-records
description: Search Mendocino County's public NextRequest archive for prior PRA requests and released records, preserving query provenance, request history, and disappearing document links.
---

# Harvest the public NextRequest archive

1. Search case numbers with hyphen and underscore variants, predecessor IDs,
   resolution IDs, applicant names, agency names, addresses, APNs, grant and
   permit identifiers, and distinctive phrases.
2. Use the anonymous `/client/requests` endpoint with `search_term` and
   `page_number`; paginate to the reported total.
3. Record every query term. NextRequest tokenization is fuzzy and may return
   unrelated records.
4. Review each request's full text before associating it with a case.
5. Capture request metadata from `/client/requests/<id>` and public history from
   `/client/requests/<id>/timeline`.
6. Enumerate current released records through `/client/request_documents` with
   the request ID.
7. Download public documents immediately, verify MIME type, hash the originals,
   and register them in the case manifest.
   Use `npm run fetch:pra-docs -- <document-id> [...]` for public PDFs.
8. Preserve request entries even when their document list is empty. A timeline
   may establish that documents were released previously but are no longer
   displayed.
9. Snapshot the global public document catalog with
   `npm run inventory:pra-docs`. Search exact request IDs there before
   concluding that an attachment has disappeared from every public portal view.
10. Follow references to earlier or related requests; productions may be
   incorporated by reference rather than duplicated.
11. Search official recipients, Coastal Commission records, County meeting
    packets, web archives, and stable filename variants for every missing
    production.
12. Keep discovered public requests separate from outbound draft requests.
    Store them in `public-request-index.yaml`, not `records-requests.yaml`.

Use `npm run search:pra` for the default case vocabulary or pass quoted search
terms explicitly. Use `--json` for machine-readable output.
