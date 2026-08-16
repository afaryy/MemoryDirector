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

variable "api_image" {
  type        = string
  description = "Immutable Artifact Registry image reference for the API."
  default     = "unused"
}

variable "web_image" {
  type        = string
  description = "Immutable Artifact Registry image reference for the web app."
  default     = "unused"
}

variable "service" {
  type        = string
  description = "Service state to manage: api, web, or all."
  default     = "all"
  validation {
    condition     = contains(["api", "web", "all"], var.service)
    error_message = "service must be api, web, or all."
  }
}

variable "api_base_url" {
  type        = string
  description = "API URL baked into the web image when managing web independently."
  default     = null
}

locals {
  common      = jsondecode(file(coalesce(var.common_config, "${path.module}/../../projects/config/common-environment.json")))
  environment = jsondecode(file(var.environment_config))
  project     = jsondecode(file(var.project_config))
  labels      = merge(try(local.common.labels, {}), try(local.environment.labels, {}), try(local.project.labels, {}))
  region      = coalesce(try(local.environment.region, null), try(local.project.region, null), try(local.common.default_region, null))
  name_prefix = local.project.resource_name
}

provider "google" { project = local.project.project_id }

module "app" {
  source       = "../../modules/foundations/app"
  project_id   = local.project.project_id
  region       = local.region
  name_prefix  = local.name_prefix
  api_image    = var.api_image
  web_image    = var.web_image
  service      = var.service
  api_base_url = var.api_base_url
}

output "configuration_summary" {
  value = {
    project_id  = local.project.project_id
    environment = local.environment.environment
    region      = local.region
    labels      = local.labels
  }
}

output "api_uri" { value = module.app.api_uri }
output "web_uri" { value = module.app.web_uri }
