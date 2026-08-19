variable "project_id" { type = string }
variable "region" { type = string }
variable "resource_name" { type = string }

variable "mcp_image" {
  type    = string
  default = "ghcr.io/clickhouse/mcp-clickhouse@sha256:f4d9f1502a14a98fd17f3ecf8654bd102ba5b1a5bde86e54a9579ed8871ef8d7"
}

variable "enable_mcp" {
  type    = bool
  default = false
}

variable "mcp_secret_project_id" {
  type    = string
  default = null
}

variable "mcp_invoker_service_account_email" {
  type    = string
  default = null
}
