output "state_bucket_name" {
  value       = module.bootstrap_state.state_bucket_name
  description = "Long-lived backend bucket name for subsequent Terraform roots."
}
