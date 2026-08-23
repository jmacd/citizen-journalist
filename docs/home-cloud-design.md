# Mendo Observatory: home-primary cloud architecture

Mendo Observatory remains a monorepo containing several independently runnable
programs. The dedicated home installation is the archival and editorial
primary. Azure provides public access, elastic document analysis, model
inference, workflow coordination, and off-site replicas.

The initial home installation is the existing Linux ARM64 `watershop` machine.
Its concrete NFS, MinIO, systemd, security, and Terraform integration is
described in the [watershop deployment profile](../deploy/watershop/README.md).
Host-level provisioning remains in `jmacd/caspar.water`; Observatory
application code remains in this monorepo.

Observatory has two software deployments: watershop staging and Azure
production. GitHub Actions promotes the exact immutable artifact accepted in
staging; production does not rebuild it. The NFS Archive remains the
preservation primary even though the software running beside it is the staging
deployment.

## Major programs

| Program | Responsibility |
| --- | --- |
| **Archive** | Writes immutable objects and ingestion events to the NFS-backed preservation layout |
| **Corpus** | Replays Archive events, builds global catalogs, verifies integrity, and creates immutable releases |
| **Docket** | Provides the PostgreSQL workflow API for jobs, approvals, conversations, research leads, and requests |
| **Pipeline** | Acquires records and runs OCR, transcription, normalization, and structured extraction jobs |
| **Relay** | Moves workflow state, Azure analysis inputs/results, archival backups, and publication releases between home and cloud |
| **Workbench** | Provides the private local CIO interface for review, approval, corpus inspection, and operations |
| **Atlas** | Manages replaceable ontologies, proposed facts, evidence locators, review, and knowledge releases |
| **Casebook** | Provides the public evidence explorer and conversational application |

These are program and responsibility boundaries, not separate repositories.
They may share contracts and libraries in this repository while running as
different processes where isolation or scaling requires it.

## Deployment and data flow

```mermaid
flowchart LR
    USER["Public user"]
    CIO["CIO"]

    subgraph HOME["Observatory Station — dedicated home machine"]
        WORKBENCH["Workbench<br/>private CIO application"]
        ARCHIVE[("Archive<br/>NFS objects and event log")]
        PIPELINE["Pipeline<br/>acquisition and local processing"]
        CORPUS["Corpus<br/>event replay, global catalogs,<br/>verification and release builder"]
        CATALOGS[("Global Parquet catalogs")]
        ATLAS["Atlas<br/>ontology and evidence-backed facts"]
        RELAY["Relay<br/>outbound synchronization")]
    end

    subgraph AZURE_CONTROL["Azure control and analysis plane"]
        DOCKET["Docket API"]
        POSTGRES[("PostgreSQL<br/>workflow and conversations")]
        FOUNDRY["Microsoft Foundry<br/>agent reasoning"]
        ANALYSIS["Document Intelligence<br/>and Speech"]
        ANALYSIS_BLOB[("Analysis interchange Blob")]
        ARCHIVE_BACKUP[("Private archival Blob<br/>objects and events")]
        RELEASE_BLOB[("Immutable corpus releases<br/>in Azure Blob Storage")]
    end

    subgraph AZURE_PUBLIC["Azure public plane"]
        MATERIALIZE["Release materializer"]
        CLOUD_CORPUS[("Cloud-local corpus snapshot<br/>read-only application input")]
        PROJECTION["Index and static-site builders"]
        SEARCH[("Azure AI Search<br/>rebuildable projection")]
        STATIC[("Generated static assets")]
        CASEBOOK["Casebook API and web application"]
    end

    CIO --> WORKBENCH
    WORKBENCH --> DOCKET
    WORKBENCH --> ATLAS
    WORKBENCH --> ARCHIVE

    PIPELINE -->|"objects and immutable events"| ARCHIVE
    ARCHIVE -->|"replayable input"| CORPUS
    CORPUS --> CATALOGS
    CATALOGS -->|"evidence locators"| ATLAS

    PIPELINE -->|"analysis input"| ANALYSIS_BLOB
    ANALYSIS_BLOB --> ANALYSIS
    ANALYSIS -->|"versioned results"| ANALYSIS_BLOB
    RELAY -->|"retrieve and validate results"| ANALYSIS_BLOB
    RELAY --> ARCHIVE

    RELAY <-->|"workflow commands and status"| DOCKET
    DOCKET --> POSTGRES
    RELAY <-->|"agent calls"| FOUNDRY
    CASEBOOK <-->|"evidence-grounded reasoning"| FOUNDRY

    ARCHIVE -->|"content-addressed backup"| ARCHIVE_BACKUP
    CORPUS -->|"verified immutable release"| RELEASE_BLOB
    RELEASE_BLOB --> MATERIALIZE
    MATERIALIZE --> CLOUD_CORPUS
    CLOUD_CORPUS --> PROJECTION
    PROJECTION --> SEARCH
    PROJECTION --> STATIC
    SEARCH --> CASEBOOK
    STATIC --> CASEBOOK

    USER --> CASEBOOK
    CASEBOOK -->|"conversation and research leads"| DOCKET
```

## Current corpus implementation

The initial corpus uses ordinary NFS files, versioned JSON events, global
Parquet catalogs, and immutable Azure Blob releases. Python components:

- write content-addressed objects and finalized event segments;
- replay events into global catalogs;
- verify object and catalog hashes;
- create a release manifest only after all referenced objects exist;
- upload archival objects without propagating deletion;
- publish a release by conditionally updating a channel pointer; and
- materialize a verified release into a cloud-local read-only snapshot.

Cloud applications serve files and APIs from the materialized snapshot or
projections built from it. They do not read the home NFS mount or translate
user requests into remote filesystem operations.

## Watertown evaluation

Watertown remains an intended experiment and may run as a shadow corpus:

- import the same NFS Archive events into a pond;
- compare Watertown catalogs and hashes with the Python implementation;
- exercise push, pull, clone, restore, query, and static-site generation;
- identify changes needed in Watertown through real Observatory workloads; and
- remain removable without changing the preservation format.

Watertown is not currently required to serve files, run the workflow, preserve
the only copy, or start Casebook. It may become the preferred propagation and
reproducible file-processing substrate after restore, replay, migration, and
parity tests demonstrate value and sufficient reliability.

## Corpus layout

Use one flat directory for each collection, including planning cases, legal
text repositories, agency archives, meeting series, and records-request
releases. This layout is also compatible with later Watertown import:

```text
/collections/UM_2025-0004/
  <record-id>--original--<hash12>.pdf
  <record-id>--pages--<processor-version>.parquet
  <record-id>--transcript--<processor-version>.parquet

/collections/california-water-code/
  <record-id>--original--<hash12>.html
  <record-id>--sections--<processor-version>.parquet

/catalog/
  records.parquet
  objects.parquet
  renditions.parquet
  provenance-events.parquet
  relationships.parquet
  collection-memberships.parquet
```

The catalogs are global because records and legal authorities may belong to
many collections. The collection path is a physical partition and convenient
inspection boundary, not the canonical record identity.

## Replaceability and recovery

Archive writes an implementation-neutral stream of immutable objects and
versioned events. A fresh system must be able to start with:

- an empty PostgreSQL database;
- an empty corpus workspace;
- no search index;
- no ontology or extracted fact tables; and
- the prior Archive export alone.

It must then verify object hashes, replay record and provenance events, import
the corpus into a new layout, rebuild global catalogs, and optionally reprocess
derivatives using current tools. PostgreSQL workflow state, search indexes,
ontologies, public applications, and any Watertown pond are replaceable around
that preserved document history.

During bootstrap, these representations remain independently recoverable:

1. NFS Archive objects and events to a private archival Blob container.
2. Verified immutable corpus releases in a separate release prefix or
   container.
3. Any experimental Watertown pond in its own remote, when enabled.

This prevents a defect in a catalog builder, release builder, or experimental
filesystem from becoming the only surviving copy.
