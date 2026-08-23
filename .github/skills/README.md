# Prototype planning-casebook skills

These skills describe repeatable, evidence-first workflows discovered while
building the UM_2025-0004 casebook. They are deliberately narrow prototypes:
each requires provenance, preserves conflicting versions, and reports missing
evidence rather than manufacturing a complete answer.

The skills assume:

- curated case metadata under `cases/<case-id>/`;
- immutable originals and generated indexes under ignored `captures/`;
- `npm run build:case-db` to rebuild the local SQLite corpus; and
- `npm run query:case -- <FTS query>` for page-level retrieval.

For Mendocino County records, use `harvest-govaccess-meeting-archive` for the
meeting publication feed and `harvest-etrakit-case-record` for case-centered
Planning projects and current attachments. Use
`harvest-nextrequest-public-records` to find earlier County PRA requests and
records already released to the public.
