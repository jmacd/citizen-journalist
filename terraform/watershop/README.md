# Watershop Terraform

This root provisions only the Mendo Observatory staging application on the
existing `watershop` host. It has independent local state and does not import,
modify, or depend on Terraform from another repository.

Existing host services are prerequisites:

- SSH access for the unprivileged service user through the local SSH agent;
- Python 3.11, `venv`, `flock`, `findmnt`, and user systemd;
- an NFS mount containing the configured staging archive path; and
- a reachable MinIO service and credentials authorized for the dedicated
  release bucket.

Copy `terraform.tfvars.example` to the ignored `terraform.tfvars`, pin the SSH
host key, add MinIO credentials, and set `observatory_revision` to the complete
committed Git revision being deployed. The Terraform SSH provisioner uses the
local SSH agent so passphrase-protected keys remain outside Terraform state.
Terraform 1.5 cannot directly enforce a literal server key through its SSH
provisioner, so a deterministic `ssh-keyscan` preflight must match the pinned
key before any provisioner can run; the key fingerprint is also part of each
deployment trigger.
Enable `deploy_observatory` only after reviewing the plan:

```sh
terraform -chdir=terraform/watershop init
terraform -chdir=terraform/watershop plan
terraform -chdir=terraform/watershop apply
```

The source packager rejects a dirty Observatory, watershop deployment,
Terraform, or workflow tree and archives exactly the pinned commit. The pinned
revision may be an ancestor of `HEAD`, allowing Terraform-only maintenance
without redeploying an unchanged runtime. Terraform generates the staging
archive UUID and Ed25519 receipt key unless an existing archive UUID is
explicitly supplied. The private key remains in local Terraform state and the
generated mode-`0600` `receipt.env`, which is loaded only by the
receipt-producing smoke unit. Both identity resources are protected from
destruction and remain stable when deployment is disabled.

After applying, configure the non-secret public key in the protected GitHub
`production` environment:

```sh
terraform -chdir=terraform/watershop \
  output -raw observatory_receipt_public_key
```

No Terraform resource in this root manages the watershop host, NFS exports,
MinIO service, unrelated buckets, Caddy, or any other project.

## Private Workbench

Set `workbench_identity_enabled = true` to create and retain the private proxy
token. Set `foundry_identity_enabled = true` to create a dedicated Entra
application and service principal with `Foundry User` at the configured project
scope. Terraform places its generated client secret only in sensitive local
state and the host's mode-`0600` environment.

Set `deploy_workbench = true` to install both the Foundry case chat and evidence
Workbench, their native Python environment, user systemd units, accepted case
and corpus links, and NFS-backed operational research queue. Chat binds only to
`127.0.0.1:4174`; Workbench binds only to `127.0.0.1:4180`. Candidate bytes,
queue decisions, and run state remain under
`/home/citizen/journalist/research`.

Terraform generates a stable proxy token protected from destruction. Leave
`workbench_identity_enabled` enabled after its first apply, even when pausing
the runtime. Retrieve
it for the host-owned Caddy configuration with:

```sh
terraform -chdir=terraform/watershop output -raw workbench_proxy_token
```

Use `deploy/watershop/Caddyfile.workbench.example` to configure a dedicated
private hostname, Caddy `basic_auth`, and the matching proxy header. Terraform
does not install or reload that snippet because Caddy is shared host
infrastructure.

For initial private testing, set
`workbench_loopback_testing_enabled = true`. This omits the proxy token from the
running service and permits Workbench requests only from its loopback listener.
Connect from the workstation with:

```sh
ssh -N \
  -L 4174:127.0.0.1:4174 \
  -L 4180:127.0.0.1:4180 \
  watershop
```

Then open `http://127.0.0.1:4174/casebook.html` and
`http://127.0.0.1:4180/workbench`. Disable loopback testing before routing
Workbench through Caddy.

The corpus archive UUID and receipt key use a separate
`observatory_identity_enabled` lifecycle. Enable it before the first corpus
runtime deployment and leave it enabled thereafter; `prevent_destroy` blocks
accidental identity rotation. A Workbench-only plan does not create those
corpus identities.

## One-time accepted-workspace import

The dedicated Citizen Journalist NFS export is mounted at
`/home/citizen/journalist`. Terraform initializes the pinned append-only
archive at `/home/citizen/journalist/archive`.

Set `accepted_workspace_identity_enabled = true` and
`import_accepted_workspace = true` for the first reviewed apply. Terraform
packages the ignored local `captures/` tree, the curated case directory, and
generated casebook data. SQLite files are copied with the online backup API and
must pass `PRAGMA integrity_check`. The package carries a complete SHA-256
inventory.

On watershop, Terraform verifies the transport package, invokes
`mendo-archive snapshot`, verifies the complete content-addressed archive,
restores the snapshot into a new clean directory, and checks both restored
SQLite databases. The snapshot UUID is retained in Terraform state with
`prevent_destroy`. After the successful import, copy the
`accepted_workspace_sha256` output to
`accepted_workspace_transport_sha256`, remove the completed import resource
from state, and set `import_accepted_workspace = false`. Keep
`accepted_workspace_identity_enabled = true`. Routine plans then retain the
snapshot identity without rebuilding or repeating the import.
