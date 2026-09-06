output "artifact_repository_id" { value = module.registry.repository_id }
output "media_bucket_name" { value = module.media_bucket.name }
output "agent_staging_bucket_name" { value = module.agent_staging_bucket.name }
output "secret_ids" { value = sort([for secret in module.secrets : secret.id]) }
output "runtime_service_account_email" { value = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com" }
output "agent_runtime_service_account_email" { value = local.agent_runtime_email }
output "agent_mcp_invoker_member" { value = "serviceAccount:${local.agent_runtime_email}" }
output "agent_runtime_project_roles" { value = sort(tolist(local.agent_runtime_project_roles)) }
output "mcp_uri" {
  value = try(module.mcp[0].uri, null)
}
output "consent_event_writer_uri" { value = try(module.consent_event_writer[0].uri, null) }
