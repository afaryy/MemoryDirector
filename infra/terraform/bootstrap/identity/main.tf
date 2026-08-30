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

locals {
  environment = jsondecode(file(var.environment_config))
  project     = jsondecode(file(var.project_config))
}

provider "google" { project = local.project.project_id }

module "bootstrap_identity" {
  source = "../../modules/foundations/bootstrap_identity"

  project_id          = local.project.project_id
  github_owner        = split("/", local.project.github_repository)[0]
  github_repo         = split("/", local.project.github_repository)[1]
  github_repositories = toset([local.project.github_repository, "sailing-together/MemoryDirector"])
  allowed_ref         = "refs/heads/main"
  environment         = local.environment.environment
  service_account_id  = "github-terraform-sandbox"
  project_roles       = var.project_roles
}
