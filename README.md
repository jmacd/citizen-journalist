# Citizen Journalist

A public-interest evidence system for finding the stories hidden across
Mendocino County planning records. It preserves and reads source documents at
scale, tests official claims against the record, and develops cited findings
about matters planning commissioners, departments, and residents should know.
It is designed to surface consequential omissions and conflicts—including
facts an institution may not emphasize—without treating agent output as
evidence or publishing claims that the sources do not support.

The initial investigation retrieves and compares Mendocino County coastal-code
publications with the California Coastal Commission's certified Local Coastal
Program records. Internal component and asset names retain their existing
identities while the broader system develops beyond that first investigation.

## Investigation report

See [Ordinance 3857 and the Mendocino County Coastal Code Discrepancy](docs/ordinance-3857-discrepancy.md)
for the shareable explanation of the evidence, internal LUP/IP conflict,
MuniCode history, unresolved certification question, and records needed for a
definitive answer.

## Planning casebook pilot

The first case-centered evidence inventory follows Mendocino Unified School
District's six-year water-system proceeding through County permits, Coastal
Commission appeals, CEQA documents, and the August 20, 2026 hearing:

- [UM_2025-0004 case inventory](cases/UM_2025-0004/README.md)
- [Machine-readable manifest](cases/UM_2025-0004/manifest.yaml)

The new [Observatory preservation services](observatory/README.md) implement
content-addressed NFS ingestion, immutable corpus events, integrity checks, and
rebuildable global Parquet catalogs.

Build a local SQLite corpus from the case manifest, question records,
water-authority map, and captured PDFs:

```sh
npm run build:case-db
npm run query:case -- '"emergency drought"'
npm run query:case -- 'groundwater AND monitoring'
```

The generated database is ignored beneath
`captures/cases/UM_2025-0004/casebook.sqlite`. It preserves document identities
and versions, page-level extracted text with full-text search, meeting cycles,
questions and cited claims, statutory authorities, institutional roles, distinct
boundary concepts, and priority missing records. Curated metadata remains in
Git under `cases/UM_2025-0004/`; downloaded originals and generated indexes do
not.

## Government observatory agents

The local-first [Microsoft Agent Framework sidecar](agents/README.md) turns the
casebook procedures into a resumable five-role evidence workflow: Case Worker,
Scout, Archivist, Analyst, and Skeptic. It uses the existing SQLite/FTS corpus,
hashes the repository skills in force, stages public records without bypassing
access controls, validates citations deterministically, and pauses for CIO
approval before canonical knowledge changes or external communication.

See the [high-level design diagram](docs/high-level-design.md) for the evidence
authority, agent workflow, public-chat boundary, CIO gates, and current Azure
deployment. The [home-primary cloud architecture](docs/home-cloud-design.md)
defines the target monorepo programs, NFS preservation boundary, Watertown pond
evaluation, PostgreSQL workflow plane, immutable Blob releases, and cloud-local
Casebook deployment. The [watershop deployment profile](deploy/watershop/README.md)
maps that design onto the existing Linux ARM64 host, NFS mount, MinIO service,
and user-level systemd conventions.

Run the first read-only public utility locally:

```sh
npm run chat
```

Open `http://127.0.0.1:4173/casebook.html`. Chat answers expose claim-level
page or recording-timestamp citations and queue unresolved records for local
research triage without sending requests. The
[Azure deployment milestone](deploy/azure/README.md) containerizes this same
evidence boundary for Container Apps and Foundry, with Azure Speech and AI
Search as the next transcription and retrieval adapters.

The reusable [cross-case government model](government-model/README.md) keeps
institutions, jurisdictions, instruments, boundaries, procedures, relationships,
and unresolved proposals distinct. The [monitor registry](monitors/README.md)
defines nine County and State publication surfaces with explicit cursor,
fingerprint, access-failure, and evidence-routing semantics.

## Visual explorer

Build the explorer from the latest captured Division II and CodeBank history
inventories, then serve it locally:

```sh
npm run explorer
```

Open `http://127.0.0.1:4173`. The explorer links the current Title 20 hierarchy,
County adoption, Coastal Commission certification, MuniCode publication
history, and the Ordinance 3857 evidence chain. Open
`http://127.0.0.1:4173/casebook.html` for the UM_2025-0004 evidence navigator,
including its permit lineage, timeline, searchable source inventory, and open
questions.

## Capture a MuniCode section

The preferred fetcher discovers the current MuniCode supplement and node ID,
then retrieves the section through the same public JSON APIs used by the web
application:

```sh
npm run fetch:section -- \
  --section 20.376.015 \
  --expect 'Alternative Energy Facilities: Off-site' \
  --expect 'Ord. No. 3857'
```

It preserves the raw API response, exact section HTML, normalized text, TOC
lineage, discovery responses, current supplement metadata, request log,
timestamps, and SHA-256
hashes beneath `captures/api/<section>/<UTC timestamp>/`. Section lookup does
not rely on a saved node ID, so it survives MuniCode TOC migrations.
Title 20 lookups are constrained to coastal **Division II** unless overridden
with `--division`. Single-section retrieval uses MuniCode's
`groupChunks=false` option so adjacent chapter sections are not downloaded.

### Rendered browser capture

The browser fetcher renders MuniCode's JavaScript application with the locally
installed Chrome browser. Each run preserves:

- rendered HTML and plain text;
- a full-page PNG and PDF;
- a sanitized HAR with response content;
- relevant public network-response bodies; and
- timestamps, expected-text results, environment details, and SHA-256 hashes.

Install dependencies:

```sh
npm install
```

Capture §20.376.015:

```sh
npm run fetch -- \
  'https://library.municode.com/ca/mendocino_county/codes/code_of_ordinances?nodeId=MECOCO_TIT20ZOOR_DIVIIMECOCOZOCO_CH20.376URREDI_S20.376.015COUSRRDI' \
  --expect '20.376.015' \
  --expect 'Conditional Uses for RR Districts'
```

Artifacts are written beneath `captures/<node-id>/<UTC timestamp>/`. Captures
are ignored by Git because HAR and page content may contain volatile request
metadata. The saved HAR removes cookies and authorization-related headers, but
review it before sharing.

Use `--headed` if the site behaves differently in headless mode. Override the
browser path with `CHROME_PATH` or `--chrome`, and the 120-second timeout with
`--timeout <seconds>`.

The command exits with status `2` if any `--expect` value is missing while
retaining all artifacts for diagnosis.

## Inventory coastal Division II

Capture the current Division II TOC, every chapter API response, document
metadata, source-note ordinance numbers, current-supplement change flags, and
byte counts:

```sh
npm run inventory:division-ii
```

The snapshot is written beneath
`captures/inventory/division-ii/<UTC timestamp>/`.

Inventory the MuniCode CodeBank versions and the “Recent Changes” entries that
belong specifically to Division II:

```sh
npm run history:division-ii
```

This history begins with the earliest version retained by MuniCode; it is not a
substitute for the Coastal Commission's certified LCP amendment record.

Trace a section and selected text across every retained MuniCode CodeBank
version:

```sh
npm run trace:section -- \
  --section 20.376.015 \
  --text 'Alternative Energy Facilities: Off-site' \
  --text 'Ord. No. 3857'
```

The trace resolves each archived version's own TOC node ID and records text
hashes, source notes, presence checks, retrieval errors, and transitions.

## Tests

```sh
npm test
```
