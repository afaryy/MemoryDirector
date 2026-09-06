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

variable "agent_engine_resource" {
  type        = string
  description = "Smoke-tested Agent Engine resource used by the production API."
  default     = null
  validation {
    condition = var.agent_engine_resource == null || can(regex(
      "^projects/(?:[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{6,30})/locations/[a-z]+(?:-[a-z0-9]+)*/reasoningEngines/[0-9]+$",
      var.agent_engine_resource,
    ))
    error_message = "agent_engine_resource must be a full reasoningEngines resource name."
  }
}
