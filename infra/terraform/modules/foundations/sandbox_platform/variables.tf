variable "project_id" { type = string }
variable "region" { type = string }
variable "resource_name" { type = string }

variable "mcp_image" {
  type    = string
  default = "ghcr.io/clickhouse/mcp-clickhouse:v0.4.1"
}

variable "enable_mcp" {
  type    = bool
  default = false
}

variable "mcp_secret_project_id" {
  type    = string
  default = null
}
