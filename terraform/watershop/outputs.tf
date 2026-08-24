output "observatory_archive_id" {
  description = "Pinned identity of the watershop staging archive."
  value       = local.archive_id
}

output "observatory_receipt_key_id" {
  description = "Identifier embedded in signed staging receipts."
  value       = local.receipt_key_id
}

output "observatory_receipt_public_key" {
  description = "Non-secret OpenSSH public key for GitHub receipt verification."
  value       = tls_private_key.staging_receipt.public_key_openssh
}

output "observatory_source_sha256" {
  description = "SHA-256 of the deterministic committed-source deployment archive."
  value       = var.deploy_observatory ? local.source_hash : null
}
