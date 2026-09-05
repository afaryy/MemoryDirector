variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "service" {
  type = string
  validation {
    condition     = contains(["api", "web", "all"], var.service)
    error_message = "service must be api, web, or all."
  }
}
variable "api_base_url" {
  type    = string
  default = null
}

variable "public_ingress" {
  type        = bool
  description = "Whether Cloud Run accepts direct public ingress before public-edge lockdown."
  default     = true
}

variable "mcp_endpoint" {
  type        = string
  description = "Private Cloud Run endpoint for the official ClickHouse MCP server."
  default     = null
}

variable "mcp_secret_project_id" {
  type        = string
  description = "Project containing clickhouse-credentials, when it differs from the app project."
  default     = null
}

variable "consent_event_writer_endpoint" {
  type        = string
  description = "Private Cloud Run endpoint for anonymous consent event recording."
  default     = null
}
