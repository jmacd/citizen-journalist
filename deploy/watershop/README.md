# Observatory Station on watershop

The first Observatory Station runs continuously on `watershop`, the Linux
ARM64 host already provisioned by `jmacd/caspar.water`. This repository owns
the Observatory programs, schemas, and service definitions. The
`caspar.water` repository remains the authority for shared-host Terraform,
including host access, NFS mounts, MinIO, Caddy, and common system packages.

Watershop runs the **staging software deployment**. Azure runs the promoted
**production software deployment**. The NFS Archive on watershop remains the
preservation primary; staging does not mean the original records are
disposable.

## Existing host conventions

The initial deployment follows the patterns already used on watershop:

- services run as the unprivileged `jmacd` user;
- `loginctl enable-linger jmacd` keeps user services running after logout;
- recurring work uses user-level systemd services and timers;
- native and containerized ARM64 workloads are both supported;
- private environment files are mode `0600` and are not committed;
- local MinIO is reachable from the host at `http://localhost:9000`;
- MinIO uses S3 region `us-east-1` and path-style bucket URLs;
- NFS-backed source archives are mounted under `/home/shared`; and
- Caddy is the host HTTP server, but Workbench is not publicly exposed.

These are integration constraints, not permission to modify or reset existing
Caspar Water ponds, buckets, timers, or archives.

## Proposed Observatory paths

The exact NFS export is a deployment variable. Use these defaults once the
directory is provisioned:

```text
/home/shared/observatory/archive/
  objects/
  events/
  envelopes/
  collections/
  exports/

/home/shared/observatory/staging/archive/
  archive.json
  objects/
  events/
  catalog/
  releases/

/home/jmacd/observatory/
  config/
  env/
  run/
  releases/
  work/
```

The NFS tree is the preservation boundary. Local runtime state, temporary
downloads, virtual environments, sockets, and materialized releases stay under
`/home/jmacd/observatory` and must be reconstructible.

The preservation primary and staging archive are distinct. New builds run
against `/home/shared/observatory/staging/archive`, never directly against
`/home/shared/observatory/archive`. Import or snapshot records into staging
deliberately; keep synthetic fixtures out of the preservation primary.

## MinIO bootstrap buckets

Use dedicated buckets rather than reusing existing Watertown buckets:

| Bucket | Contents | Mutation rule |
| --- | --- | --- |
| `mendo-archive` | Content-addressed objects and finalized event segments | Create-if-absent; no mirrored deletion |
| `mendo-releases` | Immutable release manifests, catalogs, and referenced objects | New release prefixes only |
| `mendo-analysis` | Test analysis inputs and returned results | Retention-controlled interchange |
| `mendo-watertown-shadow` | Optional experimental pond remote | Never the only corpus copy |

MinIO is the initial integration target for backup, materialization, failure,
and replay tests. Azure Blob uses the same logical separation after the local
workflow is proven. Successful MinIO replication does not by itself establish
an off-site backup.

Credentials are supplied by the existing Terraform secret pattern through an
ignored `terraform.tfvars` and generated mode-`0600` environment files. They
must not appear in Terraform remote-exec command strings, repository files,
service definitions, or logs.

## Initial services

Begin with a small number of Python processes rather than one service per
agent:

| Unit | Program | Initial schedule |
| --- | --- | --- |
| `mendo-docket.service` | Local development instance of the workflow API, until managed PostgreSQL is introduced | continuous |
| `mendo-relay.service` | PostgreSQL/outbox consumer and cloud-result synchronizer | continuous |
| `mendo-pipeline@.service` | Acquisition or document-processing job worker | queue activated |
| `mendo-corpus.service` | Event replay, catalog build, integrity verification, and release build | oneshot |
| `mendo-corpus.timer` | Starts the corpus build after new finalized events | periodic initially |
| `mendo-workbench.service` | Private CIO API and UI | continuous, loopback or private LAN only |

Agent roles run inside Pipeline, Atlas, Workbench, or Casebook workflows and
call Microsoft Foundry as needed. They are not separate systemd services.

Every unit must:

- fail nonzero on invalid configuration or corrupted input;
- use explicit memory and execution-time limits appropriate to watershop;
- write structured operational logs without document or conversation content;
- leave NFS objects and finalized event files immutable;
- tolerate temporary loss of MinIO, PostgreSQL, Azure, or Foundry; and
- resume work using stable event and job identifiers.

Only the first manual units currently exist:

- `mendo-corpus-staging.service` creates and pushes the staging release;
- `mendo-corpus-smoke.service` materializes that MinIO channel into a clean,
  retained directory.

Install them from a watershop checkout:

```sh
deploy/watershop/install-staging.sh
```

The first invocation creates
`/home/jmacd/observatory/env/staging.env` and exits until its image digest and
MinIO credentials are configured. Initialize the staging archive explicitly:

```sh
podman run --rm \
  --userns=keep-id \
  --user "$(id -u):$(id -g)" \
  --volume /home/shared/observatory/staging/archive:/archive:rw \
  <observatory-image-by-digest> \
  mendo-archive init --root /archive --birthplace watershop-staging
```

Copy the resulting `archive_id` into `MENDO_STAGING_ARCHIVE_ID` in
`staging.env`. Both runners require the canonical staging path and this exact
identity. A missing mount, substituted archive, or accidental preservation
primary path fails the unit instead of being reported as a skipped success.
The publication runner rebuilds and verifies the corpus on every invocation,
but reuses the current staging release when its file hashes and counts are
unchanged. It does not advance the channel or accumulate duplicate releases.

Then run the loop manually:

```sh
systemctl --user start mendo-corpus-staging.service
systemctl --user start mendo-corpus-smoke.service
journalctl --user -u mendo-corpus-staging.service \
  -u mendo-corpus-smoke.service --since today
```

No timer is installed yet. Scheduling begins only after repeated manual runs
show correct failure, retry, and no-change behavior.

## Deployment ownership

Changes are split deliberately:

1. This repository develops and tests Observatory programs, configuration
   templates, service units, and release artifacts.
2. `caspar.water/terraform/station/watershop` provisions host directories,
   installs approved units and artifacts, supplies secrets, and controls Caddy.
3. Routine Terraform applies must be non-destructive.
4. Any reset of Observatory workflow or derived state must be explicit and
   must never remove NFS Archive objects or events.

The first implementation milestone should prove a complete local loop:

```text
capture fixture
  -> immutable NFS object and event
  -> global Parquet catalogs
  -> verified release
  -> MinIO upload
  -> clean-directory materialization
  -> hash and catalog parity
```

Only after that loop is reproducible should Azure analysis return paths or
public Casebook releases depend on it.

The current `mendo-release push-s3` and `materialize-s3` commands implement the
MinIO portion of this loop using the standard AWS environment credential
chain. Terraform remains responsible for provisioning `mendo-releases` and
supplying its credentials through a generated mode-`0600` environment file.

## Staging-to-production promotion

Follow the deployment pattern already used by `caspar.water`:

```text
pull-request build
  -> multi-architecture immutable artifact
  -> deploy artifact to watershop staging
  -> exercise NFS -> MinIO -> clean materialization
  -> approve GitHub Actions promotion
  -> retag the same artifact as production
  -> deploy by digest to Azure
```

Production must not rebuild source code after staging acceptance. GitHub
Actions promotes the tested image or package digest so watershop and Azure run
identical program bytes with different environment configuration.

| Concern | Watershop staging | Azure production |
| --- | --- | --- |
| Runtime architecture | Linux ARM64 | Container Apps supported architecture |
| Corpus source | NFS Archive | Approved Azure corpus release |
| Object transport | Local MinIO | Azure Blob Storage |
| Workflow database | Staging PostgreSQL database/schema | Production Azure PostgreSQL |
| Model calls | Foundry staging configuration | Foundry production deployment |
| User interface | Private Workbench and staging Casebook | Public production Casebook |
| Secrets | Generated local environment files | Managed identity and Azure secret configuration |
| Deployment | Automatic staging convergence | Manual GitHub Actions promotion |

Staging and production must have separate:

- PostgreSQL databases or schemas;
- MinIO/Azure containers and channel pointers;
- service identities and credentials;
- conversation and research-lead queues;
- telemetry resources or environment labels; and
- public hostnames.

Only explicit release promotion crosses the boundary. Staging workflow state,
test conversations, synthetic records, and agent checkpoints never enter
production.
