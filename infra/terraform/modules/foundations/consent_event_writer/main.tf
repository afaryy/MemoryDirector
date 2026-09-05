terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

module "runtime" {
  source       = "../../base/service_account"
  project_id   = var.project_id
  account_id   = "memory-director-event-writer"
  display_name = "Memory Director consent event writer"
  description  = "Private Cloud Run identity with access only to ClickHouse event writer credentials."
}

module "service" {
  source                  = "../../base/cloud_run_service"
  project_id              = var.project_id
  name                    = "${var.resource_name}-consent-events"
  region                  = var.region
  image                   = var.image
  service_account_email   = module.runtime.email
  container_port          = 8000
  memory                  = "512Mi"
  timeout                 = "60s"
  ingress                 = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  allow_public_invocation = false
  invoker_members         = ["serviceAccount:${var.api_runtime_service_account_email}"]
  secret_environment_variables = {
    CLICKHOUSE_EVENT_WRITER_CREDENTIALS_JSON = { secret = var.writer_secret, version = "latest" }
  }
}

resource "google_secret_manager_secret_iam_member" "writer_secret" {
  secret_id = var.writer_secret
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.runtime.email}"
}
