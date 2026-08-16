output "state_bucket_name" {
  value       = module.state_bucket.name
  description = "Name of the long-lived Terraform state bucket."
}

output "uniform_bucket_level_access" {
  value       = module.state_bucket.uniform_bucket_level_access
  description = "Whether state bucket access is IAM-only."
}

output "public_access_prevention" {
  value       = module.state_bucket.public_access_prevention
  description = "Public access prevention mode for the state bucket."
}

output "versioning_enabled" {
  value       = module.state_bucket.versioning_enabled
  description = "Whether Terraform state versioning is enabled."
}
