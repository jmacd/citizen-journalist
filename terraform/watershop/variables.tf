variable "deploy_observatory" {
  description = "Provision the Observatory staging runtime on watershop."
  type        = bool
  default     = false
}

variable "observatory_identity_enabled" {
  description = "Create and retain the staging archive UUID and receipt key independently of runtime deployment."
  type        = bool
  default     = false
}

variable "deploy_workbench" {
  description = "Provision the private Observatory evidence Workbench on watershop."
  type        = bool
  default     = false
}

variable "workbench_identity_enabled" {
  description = "Create and retain the private Caddy-to-Workbench proxy token independently of runtime deployment."
  type        = bool
  default     = false
}

variable "observatory_revision" {
  description = "Complete committed mendo-codebook Git revision to deploy."
  type        = string
  default     = ""

  validation {
    condition = (
      var.observatory_revision == "" ||
      can(regex("^[0-9a-f]{40}$", var.observatory_revision))
    )
    error_message = "observatory_revision must be empty or a complete lowercase Git SHA."
  }
}

variable "watershop_host" {
  description = "SSH hostname or address of the existing watershop host."
  type        = string
  default     = "watershop"
}

variable "watershop_user" {
  description = "Unprivileged SSH and systemd user on watershop."
  type        = string
  default     = "jmacd"

  validation {
    condition     = var.watershop_user == "jmacd"
    error_message = "The current user units require watershop_user to be jmacd."
  }
}

variable "watershop_ssh_private_key_path" {
  description = "Local path to the SSH private key used for watershop provisioning."
  type        = string
  default     = "~/.ssh/id_ed25519"

}

variable "watershop_host_key" {
  description = "Pinned watershop SSH host public key in known_hosts format."
  type        = string
  default     = ""

  validation {
    condition = (
      var.watershop_host_key == "" ||
      can(regex("^ssh-(ed25519|rsa) [A-Za-z0-9+/]+={0,2}( .*)?$", var.watershop_host_key))
    )
    error_message = "watershop_host_key must be empty or pin an SSH Ed25519 or RSA public host key."
  }
}

variable "observatory_home" {
  description = "Reconstructible Observatory runtime root on watershop."
  type        = string
  default     = "/home/jmacd/observatory"

  validation {
    condition     = var.observatory_home == "/home/jmacd/observatory"
    error_message = "The current scripts and units require observatory_home to be /home/jmacd/observatory."
  }
}

variable "staging_archive_root" {
  description = "NFS-backed staging archive, separate from the preservation primary."
  type        = string
  default     = "/home/shared/observatory/staging/archive"

  validation {
    condition     = var.staging_archive_root == "/home/shared/observatory/staging/archive"
    error_message = "The staging safety checks require staging_archive_root to be /home/shared/observatory/staging/archive."
  }
}

variable "staging_archive_birthplace" {
  description = "Stable birthplace recorded in the staging archive identity."
  type        = string
  default     = "watershop-nfs-staging"
}

variable "observatory_archive_id" {
  description = "Existing staging archive UUID to adopt; leave empty to generate and pin one in state."
  type        = string
  default     = ""

  validation {
    condition = (
      var.observatory_archive_id == "" ||
      can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.observatory_archive_id))
    )
    error_message = "observatory_archive_id must be empty or a canonical lowercase UUID."
  }
}

variable "minio_endpoint" {
  description = "Existing MinIO S3 endpoint reachable from watershop."
  type        = string
  default     = "http://localhost:9000"
}

variable "minio_region" {
  description = "S3 region used by the existing MinIO service."
  type        = string
  default     = "us-east-1"
}

variable "minio_release_bucket" {
  description = "Observatory-owned MinIO bucket for immutable staging releases."
  type        = string
  default     = "mendo-releases"
}

variable "minio_access_key" {
  description = "MinIO access key supplied through ignored Terraform variables."
  type        = string
  sensitive   = true
  default     = ""

}

variable "minio_secret_key" {
  description = "MinIO secret key supplied through ignored Terraform variables."
  type        = string
  sensitive   = true
  default     = ""

}
