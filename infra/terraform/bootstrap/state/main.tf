terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

locals {
  common      = jsondecode(file(coalesce(var.common_config, "${path.module}/../../projects/config/common-environment.json")))
  environment = jsondecode(file(var.environment_config))
  project     = jsondecode(file(var.project_config))
  location    = coalesce(try(local.environment.region, null), try(local.project.region, null), local.common.default_region)
}

provider "google" { project = local.project.project_id }

module "bootstrap_state" {
  source = "../../modules/foundations/bootstrap_state"

  project_id  = local.project.project_id
  bucket_name = local.project.state_bucket_name
  location    = local.location
  labels = {
    environment = "sandbox"
    managed_by  = "terraform"
    project     = "memory-director"
    purpose     = "terraform-state"
  }
}
