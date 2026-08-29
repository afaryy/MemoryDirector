terraform {
  required_version = ">= 1.9.0"
  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

variable "project_config" { type = string }
variable "environment_config" { type = string }

variable "common_config" {
  type    = string
  default = null
}

variable "operation_mode" {
  type        = string
  description = "provision retains public Cloud Run ingress; lockdown follows a verified custom-domain smoke test."
  default     = "provision"

  validation {
    condition     = contains(["provision", "lockdown"], var.operation_mode)
    error_message = "operation_mode must be provision or lockdown."
  }
}

locals {
  common      = jsondecode(file(coalesce(var.common_config, "${path.module}/../../projects/config/common-environment.json")))
  environment = jsondecode(file(var.environment_config))
  project     = jsondecode(file(var.project_config))
  region      = coalesce(try(local.environment.region, null), try(local.project.region, null), try(local.common.default_region, null))
  public_edge = local.project.public_edge
}

provider "google" { project = local.project.project_id }
provider "cloudflare" {}

module "public_edge" {
  source = "../../modules/foundations/public_edge"

  project_id         = local.project.project_id
  region             = local.region
  name_prefix        = local.project.resource_name
  apex_domain        = local.public_edge.apex_domain
  cloudflare_zone_id = local.public_edge.cloudflare_zone_id
  api_path_prefix    = local.public_edge.api_path_prefix
}

output "configuration_summary" {
  value = {
    project_id     = local.project.project_id
    environment    = local.environment.environment
    region         = local.region
    operation_mode = var.operation_mode
    apex_domain    = local.public_edge.apex_domain
  }
}

output "edge_ip" { value = module.public_edge.edge_ip }
output "apex_url" { value = module.public_edge.apex_url }
output "certificate_name" { value = module.public_edge.certificate_name }
