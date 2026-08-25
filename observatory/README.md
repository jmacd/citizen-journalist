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

## Create and materialize a release

```sh
observatory/.venv/bin/mendo-release create \
  --root /home/shared/observatory/archive \
  --channel private \
  --reuse-unchanged

observatory/.venv/bin/mendo-release materialize \
  --root /home/shared/observatory/archive \
  --channel private \
  --destination /home/jmacd/observatory/releases/private-current
```

Release creation verifies the archive, freezes catalog copies, records every
referenced object and file hash in an immutable manifest, then atomically
updates the optional channel pointer. Materialization requires a new
destination, verifies every source and copied file, and renames the completed
temporary directory into place. A failure leaves no partial destination.
With `--reuse-unchanged`, creation compares verified destination hashes and
counts with the current channel manifest and returns that release instead of
creating an identical one. The option requires a channel; malformed existing
channel state is an error rather than a reason to overwrite it.

## Push to and materialize from MinIO

The S3 transport uses the standard AWS credential environment chain. On
watershop, credentials belong in the existing mode-`0600` generated environment
file, not in command arguments:

```sh
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

observatory/.venv/bin/mendo-release push-s3 \
  --root /home/shared/observatory/archive \
  --channel private \
  --bucket mendo-releases \
  --endpoint-url http://localhost:9000
```

The bucket must already exist. Push verifies local files, reuses remote
immutable keys only when length and recorded SHA-256 match, uploads the
manifest after all entries, and publishes the mutable channel pointer last.
Keys are isolated beneath the archive UUID.

Add `--verify-reused` for a slower audit push that downloads and hashes every
existing immutable key before reusing it. Without that option, reuse trusts
MinIO's object length and stored SHA-256 metadata; a later materialization
still downloads and verifies every byte.

Materialize a remote channel into a new local directory:

```sh
archive_id=$(
  python -c \
    'import json; print(json.load(open("/home/shared/observatory/archive/archive.json"))["archive_id"])'
)

observatory/.venv/bin/mendo-release materialize-s3 \
  --archive-id "$archive_id" \
  --channel private \
  --destination /home/jmacd/observatory/releases/private-current \
  --bucket mendo-releases \
  --endpoint-url http://localhost:9000
```

`mendo-release receipt` re-verifies a clean materialization against the
archive, release, and manifest identity returned by `materialize-s3`. Watershop
uses that contract as the input to `mendo-promote`, which verifies the
multi-platform image index and emits an immutable production-candidate record.
Candidate creation does not rebuild or deploy either artifact.

Every downloaded file is hashed before the completed temporary tree becomes
visible. MinIO transports a release; it does not replace the NFS Archive.

Materializing directly by `--release-id` also requires
`--expected-manifest-sha256`; the release ID alone is not an integrity anchor.
The MinIO credential needs bucket access plus `HeadBucket`, `HeadObject`,
`GetObject`, and `PutObject`. Missing-key checks intentionally fail rather than
treating `AccessDenied` as absence.

## Tests

```sh
npm run test:observatory
```

The initial suite covers immutable ingestion, content deduplication with
separate acquisition events, all six Parquet catalogs, deletion and
deterministic rebuild of catalogs, and loud corruption detection.
