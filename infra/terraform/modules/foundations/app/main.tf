terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

locals {
  media_bucket_name = "${var.project_id}-media"
  api_environment_variables = merge({
    WEB_ORIGINS                       = "*"
    GOOGLE_CLOUD_PROJECT              = var.project_id
    GOOGLE_CLOUD_LOCATION             = var.region
    MEDIA_BUCKET                      = local.media_bucket_name
    QUOTA_ENABLED                     = "true"
    QUOTA_FIRESTORE_DATABASE          = "(default)"
    TRUST_PROXY_HEADERS               = "true"
    VISITOR_DAILY_FILM_LIMIT          = tostring(var.quotas.visitor_daily_film_limit)
    IP_DAILY_FILM_LIMIT               = tostring(var.quotas.ip_daily_film_limit)
    IP_MAX_CONCURRENT_FILMS           = tostring(var.quotas.ip_max_concurrent_films)
    GLOBAL_DAILY_FILM_LIMIT           = tostring(var.quotas.global_daily_film_limit)
    GLOBAL_DAILY_FILM_HARD_MAX        = tostring(var.application_limits.global_daily_film_hard_max)
    GLOBAL_MAX_CONCURRENT_FILMS       = tostring(var.quotas.global_max_concurrent_films)
    VISITOR_DAILY_ORIGINAL_SONG_LIMIT = tostring(var.quotas.visitor_daily_original_song_limit)
    GLOBAL_DAILY_ORIGINAL_SONG_LIMIT  = tostring(var.quotas.global_daily_original_song_limit)
    MAX_FILM_DURATION_SECONDS         = tostring(var.application_limits.max_film_duration_seconds)
    MAX_MEDIA_ITEMS                   = tostring(var.application_limits.max_media_items)
    MAX_UPLOAD_FILE_MB                = tostring(var.application_limits.max_upload_file_mb)
    MAX_UPLOAD_TOTAL_MB               = tostring(var.application_limits.max_upload_total_mb)
    MAX_REQUEST_TEXT_CHARS            = tostring(var.application_limits.max_request_text_chars)
    UPLOAD_SIGNED_URL_TTL_MINUTES     = tostring(var.application_limits.upload_signed_url_ttl_minutes)
    DOWNLOAD_SIGNED_URL_TTL_MINUTES   = tostring(var.application_limits.download_signed_url_ttl_minutes)
    }, var.mcp_endpoint == null ? {} : {
    CLICKHOUSE_MCP_ENDPOINT = var.mcp_endpoint
    }, var.consent_event_writer_endpoint == null ? {} : {
    CONSENT_EVENT_WRITER_ENDPOINT = var.consent_event_writer_endpoint
    }, var.agent_engine_resource == null ? {} : {
    MEMORY_FILM_PLANNER_RESOURCE = var.agent_engine_resource
  })
}

module "api" {
  count                 = contains(["api", "all"], var.service) ? 1 : 0
  source                = "../../base/cloud_run_service"
  project_id            = var.project_id
  name                  = "${var.name_prefix}-api"
  region                = var.region
  image                 = var.api_image
  service_account_email = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com"
  container_port        = 8000
  memory                = "2Gi"
  timeout               = "${var.runtime_limits.api_timeout_seconds}s"
  min_instance_count    = var.runtime_limits.api_min_instances
  max_instance_count    = var.runtime_limits.api_max_instances
  container_concurrency = var.runtime_limits.api_concurrency
  ingress               = var.public_ingress ? "INGRESS_TRAFFIC_ALL" : "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  environment_variables = local.api_environment_variables
  secret_environment_variables = var.mcp_endpoint == null ? {} : {
    CLICKHOUSE_CREDENTIALS_JSON = {
      secret  = var.mcp_secret_project_id == null || var.mcp_secret_project_id == var.project_id ? "clickhouse-credentials" : "projects/${var.mcp_secret_project_id}/secrets/clickhouse-credentials"
      version = "latest"
    }
  }
}

module "web" {
  count                 = contains(["web", "all"], var.service) ? 1 : 0
  source                = "../../base/cloud_run_service"
  project_id            = var.project_id
  name                  = "${var.name_prefix}-web"
  region                = var.region
  image                 = var.web_image
  service_account_email = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com"
  container_port        = 3000
  min_instance_count    = var.runtime_limits.web_min_instances
  max_instance_count    = var.runtime_limits.web_max_instances
  container_concurrency = var.runtime_limits.web_concurrency
  ingress               = var.public_ingress ? "INGRESS_TRAFFIC_ALL" : "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  environment_variables = { API_BASE_URL = coalesce(var.api_base_url, try(module.api[0].uri, "")) }
}
