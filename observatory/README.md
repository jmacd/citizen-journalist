# Mendo Observatory services

This Python package begins the home-primary Observatory implementation. Its
first slice provides:

- `mendo-archive`: immutable, content-addressed object and event ingestion;
- `mendo-corpus`: integrity verification and global Parquet catalog rebuilds.

The NFS Archive is authoritative. Parquet catalogs are disposable projections
that can be deleted and rebuilt from finalized events and objects.

## Local setup

From the repository root:

```sh
python3 -m venv observatory/.venv
observatory/.venv/bin/python -m pip install --upgrade pip
observatory/.venv/bin/python -m pip install -r observatory/requirements.lock
observatory/.venv/bin/python -m pip install -e observatory --no-deps
```

## Ingest an original

Initialize the intended NFS archive once:

```sh
observatory/.venv/bin/mendo-archive init \
  --root /home/shared/observatory/archive \
  --birthplace watershop
```

This writes an immutable `archive.json` identity. Ordinary ingestion and
catalog operations refuse to proceed without that identity, preventing an
unmounted NFS path from silently becoming a new local archive.

```sh
observatory/.venv/bin/mendo-archive ingest ./record.pdf \
  --root /home/shared/observatory/archive \
  --record-id county-pc-2024-0019 \
  --title 'Resolution PC 2024-0019' \
  --collection UM_2025-0004 \
  --collection mendocino-county-resolutions \
  --source-url 'https://example.gov/record.pdf' \
  --custodian 'Mendocino County'
```

Ingestion streams the source into an NFS-local temporary file, hashes it,
flushes it, and installs it at:

```text
objects/sha256/<first-two-hex>/<sha256>
```

The object is installed create-only. Existing objects are re-read and verified
rather than overwritten. Only after the object exists does Archive finalize a
unique `object_stored` event beneath `events/<UTC-date>/`.

The finalized event is the durable commit point. A workflow database may be
updated afterward and recovered from the event if that update fails.

## Verify and rebuild catalogs

```sh
observatory/.venv/bin/mendo-corpus verify \
  --root /home/shared/observatory/archive

observatory/.venv/bin/mendo-corpus build \
  --root /home/shared/observatory/archive
```

`verify` re-hashes every distinct object referenced by an event. Missing,
truncated, corrupted, or conflicting objects fail the command.

`build` verifies first and atomically replaces six global catalogs:

```text
catalog/records.parquet
catalog/objects.parquet
catalog/renditions.parquet
catalog/provenance-events.parquet
catalog/relationships.parquet
catalog/collection-memberships.parquet
```

Records and objects are global. Collections are many-to-many groupings such as
planning cases, legal repositories, agency archives, or meeting series.

## Tests

```sh
npm run test:observatory
```

The initial suite covers immutable ingestion, content deduplication with
separate acquisition events, all six Parquet catalogs, deletion and
deterministic rebuild of catalogs, and loud corruption detection.
