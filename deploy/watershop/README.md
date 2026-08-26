# Observatory Station on watershop

The first Observatory Station runs continuously on `watershop`, an existing
Linux ARM64 host. This repository owns the Observatory programs, schemas,
service definitions, and application-level Terraform. Host access, NFS,
MinIO, Caddy, and common system packages are independently administered
prerequisites and are not managed by this project.

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
/home/citizen/journalist/archive/
  objects/
  events/
  envelopes/
  collections/
  exports/

/home/citizen/journalist/research/
  <Foundry retrieval staging bundles>

/home/jmacd/observatory/
  config/
  env/
  run/
  releases/
  work/
```

The Citizen Journalist NFS tree is the preservation boundary. Local runtime state, temporary
downloads, virtual environments, sockets, and materialized releases stay under
`/home/jmacd/observatory` and must be reconstructible.

The append-only archive and mutable research staging area are distinct. New
records enter `/home/citizen/journalist/archive` only through immutable objects
and finalized events. Foundry candidates remain under
`/home/citizen/journalist/research` until CIO approval and deterministic
registration. Keep synthetic fixtures out of the archive.

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

Credentials are supplied through this repository's ignored
`terraform/watershop/terraform.tfvars` and generated mode-`0600` environment
files. They
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
  retained directory, re-verifies its complete file set, and writes an
  immutable content-addressed staging receipt under
  `/home/jmacd/observatory/run/staging-receipts/`.
- `mendo-workbench.service` serves the private evidence inbox and candidate
  review API on port 4180. It records audited CIO decisions but does not itself
  mutate canonical manifests.

The Workbench is intended to sit behind the existing host-owned Caddy service.
This repository provides `Caddyfile.workbench.example` for a dedicated private
hostname with Caddy `basic_auth` and a proxy-only shared token. The Workbench
rejects requests that do not carry that token when it is configured. Importing
the snippet into the shared Caddy configuration remains an explicit host
administration action; this repository does not own or replace Caddy.

Terraform can instead enable explicit trusted-LAN access. Chat and Workbench
then bind directly to watershop's interfaces, while Workbench rejects source
addresses that are not private or loopback. This mode has no per-user
authentication and must be disabled before enabling the Caddy route or exposing
watershop beyond the trusted network.

Terraform is the supported installer. The standalone script only refreshes
units and scripts after a native virtual environment and environment file
already exist:

```sh
deploy/watershop/install-staging.sh
```

Both runners use the Terraform-managed native Python virtual environment at
`/home/jmacd/observatory/venv`. A missing environment, NFS mount, substituted
archive, or accidental preservation-primary path fails the unit instead of
being reported as a skipped success.
Staging receipts use Ed25519. Terraform generates the private key, retains it
only in the ignored local Terraform state, and installs its base64-encoded PEM
form in the mode-`0600` `receipt.env` loaded only by the smoke unit. Shared
MinIO and runtime settings remain in `staging.env`. GitHub receives only the
non-secret OpenSSH public key.

`terraform/watershop` provisions the Observatory application boundary. Set
the following only in its ignored `terraform.tfvars`:

```hcl
deploy_observatory           = true
observatory_revision         = "<complete committed mendo-codebook Git SHA>"
observatory_archive_id       = "" # Terraform generates and pins a UUID
```

If the staging archive already exists, set `observatory_archive_id` to its
existing UUID before enabling deployment. Terraform otherwise generates the
UUID once and refuses to adopt a different archive silently.
Setting `deploy_observatory = false` removes no host data and does not rotate
the Terraform-managed archive UUID or receipt key. Both identity resources are
protected from destruction; rotation requires an explicit configuration
change.

Then run `terraform -chdir=terraform/watershop plan` and review it before
applying. Terraform verifies that
`/home/citizen/journalist` is NFS-backed, creates only the dedicated archive,
creates the `mendo-releases` MinIO bucket, builds a versioned Python virtual
environment from the locked runtime dependencies, initializes the archive if
absent, installs the scripts, secret environment, and user units, and leaves
both publication services manual. Terraform refuses uncommitted deployment
source or a checkout that does not match `observatory_revision`. A routine
apply never silently adopts or replaces `/home/citizen/journalist/archive`.

After the first apply, copy the non-secret output into the protected GitHub
`production` environment variable:

```sh
terraform -chdir=terraform/watershop \
  output -raw observatory_receipt_public_key
```

Name the variable `MENDO_STAGING_RECEIPT_PUBLIC_KEY`. The Ed25519 private key
never enters GitHub. Replacing the Terraform `tls_private_key` resource is an
explicit key rotation and requires updating this public environment variable
before another receipt can be promoted.
The publication runner rebuilds and verifies the corpus on every invocation,
but reuses the current staging release when its file hashes and counts are
unchanged. It does not advance the channel or accumulate duplicate releases.
It also holds a nonblocking host lock for the complete create-and-push
transaction. Overlapping invocations of the staging runner exit nonzero instead
of racing the local channel or remote publication. Direct `mendo-release`
commands do not participate in this runner lock.

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
2. `terraform/watershop` provisions Observatory-owned directories, installs
   approved units and artifacts, and supplies application secrets.
3. Shared host services, NFS exports, MinIO itself, Caddy, and unrelated
   projects remain outside this repository's Terraform state.
4. Routine Terraform applies must be non-destructive.
5. Any reset of Observatory workflow or derived state must be explicit and
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

Use the following staging-to-production deployment pattern:

```text
pull-request build
  -> commit and locked Python runtime
  -> deploy native Python environment to watershop staging
  -> exercise NFS -> MinIO -> clean materialization
  -> build multi-architecture image from the same commit
  -> approve GitHub Actions promotion
  -> deploy by digest to Azure
```

Watershop validates the committed Python source and runtime lock natively.
Production uses a digest-pinned image built from that same Git revision; the
promotion gate rejects an image whose OCI revision label differs from the
signed staging receipt. The platform packaging differs, but source revision,
dependency lock, release manifest, and evidence bytes remain explicit.

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

The promotion input is the immutable staging receipt emitted by the smoke
service, not a manually reconstructed set of identifiers. The receipt records
the committed source revision, deployed source hash, runtime lock hash, Python
version, cleanly materialized archive ID, release ID, channel-derived manifest
hash, file count, byte count, verification time, and retained local path.
Promotion independently verifies the proposed production image in GHCR and
requires its OCI revision label to match the staged revision.

Submit a selected receipt to the manual promotion workflow:

```sh
gh workflow run observatory-promote.yml \
  --repo jmacd/mendo-codebook \
  -f staging_receipt="$(cat /home/jmacd/observatory/run/staging-receipts/<receipt>.json)" \
  -f production_image="ghcr.io/jmacd/mendo-codebook-observatory@sha256:<digest>"
```

The GitHub `production` environment supplies the human approval boundary. It
must require reviewers and restrict deployments to the default branch. The
workflow validates the receipt contract, resolves its exact GHCR digest,
requires both Linux ARM64 and AMD64 manifests, and uploads a typed production
candidate. It does not rebuild or deploy the image or corpus; Azure deployment
remains a later consumer of the approved candidate.
