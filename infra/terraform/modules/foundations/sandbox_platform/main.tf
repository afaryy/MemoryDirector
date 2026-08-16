terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

locals {
  required_services = toset([
    "aiplatform.googleapis.com", "artifactregistry.googleapis.com", "run.googleapis.com",
    "secretmanager.googleapis.com", "storage.googleapis.com",
  ])
  secret_ids = toset(["clickhouse-credentials", "gemini-runtime-config"])
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
  for_each  = module.secrets
  secret_id = each.value.name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.runtime.email}"
}
