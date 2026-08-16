terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

resource "google_project_service" "storage" {
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

module "state_bucket" {
  source = "../../base/gcs_state_bucket"

  project_id  = var.project_id
  bucket_name = var.bucket_name
  location    = var.location
  labels      = var.labels

  depends_on = [google_project_service.storage]
}
