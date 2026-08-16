output "artifact_repository_id" { value = module.registry.repository_id }
output "media_bucket_name" { value = module.media_bucket.name }
output "secret_ids" { value = sort([for secret in module.secrets : secret.id]) }
output "runtime_service_account_email" { value = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com" }
