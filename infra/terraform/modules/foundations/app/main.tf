terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

module "api" {
  count                 = contains(["api", "all"], var.service) ? 1 : 0
  source                = "../../base/cloud_run_service"
  project_id            = var.project_id
  name                  = "${var.name_prefix}-api"
  region                = var.region
  image                 = var.api_image
  service_account_email = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com"
  container_port        = 8000
  memory                = "1Gi"
  environment_variables = {
    WEB_ORIGINS           = "*"
    GOOGLE_CLOUD_PROJECT  = var.project_id
    GOOGLE_CLOUD_LOCATION = var.region
    MEDIA_BUCKET          = "${var.name_prefix}-media"
  }
}

module "web" {
  count                 = contains(["web", "all"], var.service) ? 1 : 0
  source                = "../../base/cloud_run_service"
  project_id            = var.project_id
  name                  = "${var.name_prefix}-web"
  region                = var.region
  image                 = var.web_image
  service_account_email = "memory-director-runtime@${var.project_id}.iam.gserviceaccount.com"
  container_port        = 3000
  environment_variables = { API_BASE_URL = coalesce(var.api_base_url, try(module.api[0].uri, "")) }
}
