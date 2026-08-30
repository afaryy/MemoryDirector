output "github_repository" { value = "${var.github_owner}/${var.github_repo}" }
output "github_repositories" { value = tolist(var.github_repositories) }
output "allowed_ref" { value = var.allowed_ref }
output "environment" { value = var.environment }
output "service_account_email" {
  value = "${var.service_account_id}@${var.project_id}.iam.gserviceaccount.com"
}
output "workload_identity_provider" { value = module.github_oidc.provider_name }
output "enabled_services" { value = tolist(local.required_services) }
