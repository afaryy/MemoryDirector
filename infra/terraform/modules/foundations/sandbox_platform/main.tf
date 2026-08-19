terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

locals {
  required_services = toset([
    "aiplatform.googleapis.com", "artifactregistry.googleapis.com", "run.googleapis.com",
    "secretmanager.googleapis.com", "storage.googleapis.com",
  ])
  runtime_secret_ids   = toset(["clickhouse-credentials", "gemini-runtime-config"])
  migration_secret_ids = toset(["clickhouse-migration-credentials"])
  secret_ids           = setunion(local.runtime_secret_ids, local.migration_secret_ids)
  mcp_secret_project   = coalesce(var.mcp_secret_project_id, var.project_id)
  mcp_secret_ref       = local.mcp_secret_project == var.project_id ? "clickhouse-credentials" : "projects/${local.mcp_secret_project}/secrets/clickhouse-credentials"
}

resource "google_project_service" "platform" {
  for_each           = local.required_services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "registry" {
  source        = "../../base/artifact_registry"
  project_id    = var.project_id
  location      = var.region
  repository_id = var.resource_name
  description   = "Memory Director sandbox images."
  depends_on    = [google_project_service.platform]
}

module "media_bucket" {
  source        = "../../base/private_media_bucket"
  project_id    = var.project_id
  bucket_name   = "${var.resource_name}-media"
  location      = var.region
  force_destroy = true
  labels        = { environment = "sandbox", managed_by = "terraform", project = "memory-director" }
  depends_on    = [google_project_service.platform]
}

module "runtime" {
  source       = "../../base/service_account"
  project_id   = var.project_id
  account_id   = "memory-director-runtime"
  display_name = "Memory Director sandbox runtime"
  description  = "Cloud Run runtime identity; no user-managed key."
  depends_on   = [google_project_service.platform]
}

module "secrets" {
  for_each   = local.secret_ids
  source     = "../../base/secret_container"
  project_id = var.project_id
  secret_id  = each.value
  depends_on = [google_project_service.platform]
}

resource "google_project_iam_member" "runtime_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${module.runtime.email}"
}

resource "google_storage_bucket_iam_member" "runtime_media" {
  bucket = module.media_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${module.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_secrets" {
  for_each = {
    for secret_id, secret in module.secrets : secret_id => secret
    if contains(local.runtime_secret_ids, secret_id)
  }
  secret_id = each.value.name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "mcp_cross_project" {
  for_each = !var.enable_mcp || local.mcp_secret_project == var.project_id ? toset([]) : toset(["clickhouse-credentials"])

  secret_id = "projects/${local.mcp_secret_project}/secrets/${each.value}"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.runtime.email}"
}

module "mcp" {
  count  = var.enable_mcp ? 1 : 0
  source = "../../base/cloud_run_service"

  project_id              = var.project_id
  name                    = "${var.resource_name}-mcp"
  region                  = var.region
  image                   = var.mcp_image
  service_account_email   = module.runtime.email
  container_port          = 8000
  allow_public_invocation = false
  invoker_members         = ["serviceAccount:${module.runtime.email}"]

  environment_variables = {
    CLICKHOUSE_MCP_SERVER_TRANSPORT = "http"
    CLICKHOUSE_MCP_BIND_HOST        = "0.0.0.0"
    CLICKHOUSE_MCP_BIND_PORT        = "8000"
    CLICKHOUSE_ALLOW_WRITE_ACCESS   = "false"
    CLICKHOUSE_ALLOW_DROP           = "false"
  }

  secret_environment_variables = {
    CLICKHOUSE_CREDENTIALS_JSON = {
      secret  = local.mcp_secret_ref
      version = "latest"
    }
  }

  command = ["python"]
  args = [
    "-c",
    "import json, os, runpy; config = json.loads(os.environ.pop('CLICKHOUSE_CREDENTIALS_JSON')); os.environ.update({key: value for key, value in config.items() if key.startswith('CLICKHOUSE_')}); runpy.run_module('mcp_clickhouse.main', run_name='__main__')",
  ]

  depends_on = [
    module.secrets,
    google_secret_manager_secret_iam_member.runtime_secrets,
    google_secret_manager_secret_iam_member.mcp_cross_project,
  ]
}
