output "name" {
  value       = google_storage_bucket.terraform_state.name
  description = "Terraform state bucket name."
}

output "uniform_bucket_level_access" {
  value       = google_storage_bucket.terraform_state.uniform_bucket_level_access
  description = "Whether IAM-only bucket access is enforced."
}

output "public_access_prevention" {
  value       = google_storage_bucket.terraform_state.public_access_prevention
  description = "Public access prevention mode."
}

output "versioning_enabled" {
  value       = google_storage_bucket.terraform_state.versioning[0].enabled
  description = "Whether GCS object versioning is enabled."
}
