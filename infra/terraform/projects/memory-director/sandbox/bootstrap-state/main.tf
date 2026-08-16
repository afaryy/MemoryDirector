terraform {
  required_version = ">= 1.9.0"

  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

module "bootstrap_state" {
  source = "../../../../modules/foundations/bootstrap_state"

  project_id  = var.project_id
  bucket_name = var.state_bucket_name
  location    = var.location
  labels = {
    environment = "sandbox"
    managed_by  = "terraform"
    project     = "memory-director"
    purpose     = "terraform-state"
  }
}
