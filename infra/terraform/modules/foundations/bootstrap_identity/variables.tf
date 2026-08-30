variable "project_id" { type = string }
variable "github_owner" { type = string }
variable "github_repo" { type = string }
variable "github_repositories" { type = set(string) }
variable "allowed_ref" { type = string }
variable "environment" { type = string }
variable "service_account_id" { type = string }
variable "project_roles" {
  type        = set(string)
  description = "Granular project roles needed by the Terraform deployment identity."
  default     = []
}
