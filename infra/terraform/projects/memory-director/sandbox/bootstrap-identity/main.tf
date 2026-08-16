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

provider "google" { project = var.project_id }

module "bootstrap_identity" {
  source = "../../../../modules/foundations/bootstrap_identity"

  project_id         = var.project_id
  github_owner       = "afaryy"
  github_repo        = "MemoryDirector"
  allowed_ref        = "refs/heads/main"
  environment        = "sandbox"
  service_account_id = "github-terraform-sandbox"
  project_roles      = var.project_roles
}
