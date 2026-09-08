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

variable "web_origins" {
  type        = string
  description = "Comma-separated browser origins allowed to call the API."
  default     = "http://localhost:3000"
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

variable "runtime_limits" {
  type = object({
    api_min_instances   = number
    api_max_instances   = number
    api_concurrency     = number
    api_timeout_seconds = number
    web_min_instances   = number
    web_max_instances   = number
    web_concurrency     = number
  })
  default = {
    api_min_instances   = 0
    api_max_instances   = 3
    api_concurrency     = 4
    api_timeout_seconds = 900
    web_min_instances   = 0
    web_max_instances   = 2
    web_concurrency     = 80
  }
}

variable "application_limits" {
  type = object({
    max_film_duration_seconds   = number
    max_media_items             = number
    media_analysis_max_attempts = number
    max_upload_file_mb          = number
    max_request_text_chars      = number
    global_daily_film_hard_max  = number
    thumbnail_max_concurrency   = number
  })
  default = {
    max_film_duration_seconds   = 60
    max_media_items             = 15
    media_analysis_max_attempts = 2
    max_upload_file_mb          = 250
    max_request_text_chars      = 2000
    global_daily_film_hard_max  = 100
    thumbnail_max_concurrency   = 2
  }
}

variable "quotas" {
  type = object({
    visitor_daily_film_limit          = number
    ip_daily_film_limit               = number
    ip_max_concurrent_films           = number
    global_daily_film_limit           = number
    global_max_concurrent_films       = number
    visitor_daily_original_song_limit = number
    global_daily_original_song_limit  = number
    visitor_daily_thumbnail_limit     = number
    ip_daily_thumbnail_limit          = number
  })
  default = {
    visitor_daily_film_limit          = 5
    ip_daily_film_limit               = 10
    ip_max_concurrent_films           = 2
    global_daily_film_limit           = 30
    global_max_concurrent_films       = 6
    visitor_daily_original_song_limit = 3
    global_daily_original_song_limit  = 20
    visitor_daily_thumbnail_limit     = 75
    ip_daily_thumbnail_limit          = 150
  }
}
