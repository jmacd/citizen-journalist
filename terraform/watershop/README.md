# Watershop Terraform

This root provisions only the Mendo Observatory staging application on the
existing `watershop` host. It has independent local state and does not import,
modify, or depend on Terraform from another repository.

Existing host services are prerequisites:

- SSH access for the unprivileged service user;
- Python 3.11, `venv`, `flock`, `findmnt`, and user systemd;
- an NFS mount containing the configured staging archive path; and
- a reachable MinIO service and credentials authorized for the dedicated
  release bucket.

Copy `terraform.tfvars.example` to the ignored `terraform.tfvars`, pin the SSH
host key, add MinIO credentials, and set `observatory_revision` to the complete
committed Git revision being deployed. Enable `deploy_observatory` only after
reviewing the plan:

```sh
terraform -chdir=terraform/watershop init
terraform -chdir=terraform/watershop plan
terraform -chdir=terraform/watershop apply
```

The source packager rejects a dirty Observatory, watershop deployment, or
workflow tree and rejects a revision other than the checked-out `HEAD`.
Terraform generates the staging archive UUID and Ed25519 receipt key unless an
existing archive UUID is explicitly supplied. The private key remains in local
Terraform state and the generated mode-`0600` `receipt.env`, which is loaded
only by the receipt-producing smoke unit. Both identity resources are protected
from destruction and remain stable when deployment is disabled.

After applying, configure the non-secret public key in the protected GitHub
`production` environment:

```sh
terraform -chdir=terraform/watershop \
  output -raw observatory_receipt_public_key
```

No Terraform resource in this root manages the watershop host, NFS exports,
MinIO service, unrelated buckets, Caddy, or any other project.
