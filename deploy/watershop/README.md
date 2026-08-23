# Observatory Station on watershop

The first Observatory Station runs continuously on `watershop`, the Linux
ARM64 host already provisioned by `jmacd/caspar.water`. This repository owns
the Observatory programs, schemas, and service definitions. The
`caspar.water` repository remains the authority for shared-host Terraform,
including host access, NFS mounts, MinIO, Caddy, and common system packages.

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
