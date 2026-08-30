variable "project_id" { type = string }
variable "pool_id" { type = string }
variable "github_repositories" { type = set(string) }
variable "allowed_ref" { type = string }
variable "environment" { type = string }
