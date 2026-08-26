output "observatory_archive_id" {
  description = "Pinned identity of the watershop staging archive."
  value       = local.archive_id != "" ? local.archive_id : null
}

output "observatory_receipt_key_id" {
  description = "Identifier embedded in signed staging receipts."
  value       = local.receipt_key_id != "" ? local.receipt_key_id : null
}

output "observatory_receipt_public_key" {
  description = "Non-secret OpenSSH public key for GitHub receipt verification."
  value       = var.observatory_identity_enabled ? tls_private_key.staging_receipt[0].public_key_openssh : null
}

output "observatory_source_sha256" {
  description = "SHA-256 of the deterministic committed-source deployment archive."
  value       = var.deploy_observatory ? local.source_hash : null
}

output "accepted_workspace_snapshot_id" {
  description = "Pinned identity of the imported accepted-workspace snapshot."
  value       = var.import_accepted_workspace ? random_uuid.accepted_workspace_snapshot[0].result : null
}

output "accepted_workspace_sha256" {
  description = "SHA-256 of the accepted-workspace transport archive."
  value       = var.import_accepted_workspace ? data.external.accepted_workspace[0].result.sha256 : null
}

output "workbench_proxy_token" {
  description = "Sensitive token Caddy must inject when proxying Workbench requests."
  value       = var.workbench_identity_enabled ? random_password.workbench_proxy[0].result : null
  sensitive   = true
}

output "workbench_source_sha256" {
  description = "SHA-256 of the deterministic committed Workbench source archive."
  value       = var.deploy_workbench ? local.workbench_source_hash : null
}
