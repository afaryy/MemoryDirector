terraform {
  required_version = ">= 1.9.0"
  backend "gcs" {}

  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

variable "project_config" { type = string }
variable "environment_config" { type = string }
variable "common_config" {
  type    = string
  default = null
}

variable "enable_mcp" {
  type    = bool
  default = false
}

variable "enable_consent_event_writer" {
  type    = bool
  default = false
}

locals {
  common             = jsondecode(file(coalesce(var.common_config, "${path.module}/../../projects/config/common-environment.json")))
  environment        = jsondecode(file(var.environment_config))
  project            = jsondecode(file(var.project_config))
  labels             = merge(try(local.common.labels, {}), try(local.environment.labels, {}), try(local.project.labels, {}))
  region             = coalesce(try(local.environment.region, null), try(local.project.region, null), try(local.common.default_region, null))
  mcp_secret_project = try(local.project.mcp_secret_project_id, local.project.project_id)
}

provider "google" { project = local.project.project_id }

module "platform" {
  source                            = "../../modules/foundations/sandbox_platform"
  project_id                        = local.project.project_id
  region                            = local.region
  resource_name                     = local.project.resource_name
  mcp_image                         = try(local.project.mcp_image, "ghcr.io/clickhouse/mcp-clickhouse@sha256:f4d9f1502a14a98fd17f3ecf8654bd102ba5b1a5bde86e54a9579ed8871ef8d7")
  enable_mcp                        = var.enable_mcp
  enable_consent_event_writer       = var.enable_consent_event_writer
  consent_event_writer_image        = try(local.project.consent_event_writer_image, null)
  mcp_secret_project_id             = local.mcp_secret_project
  mcp_invoker_service_account_email = try(local.project.mcp_invoker_service_account_email, null)
}

output "configuration_summary" {
  value = {
    project_id  = local.project.project_id
    environment = local.environment.environment
    region      = local.region
    labels      = local.labels
  }
}

output "mcp_uri" { value = module.platform.mcp_uri }
output "consent_event_writer_uri" { value = module.platform.consent_event_writer_uri }
