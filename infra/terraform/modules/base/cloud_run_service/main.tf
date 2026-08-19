terraform {
  required_version = ">= 1.9.0"
  required_providers { google = { source = "hashicorp/google", version = "~> 6.0" } }
}

resource "google_cloud_run_v2_service" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.region
  ingress             = var.ingress
  deletion_protection = false

  template {
    service_account = var.service_account_email

    scaling {
      max_instance_count = var.max_instance_count
    }

    containers {
      image   = var.image
      command = var.command
      args    = var.args

      ports {
        container_port = var.container_port
      }

      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_environment_variables
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = env.value.version
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  count    = var.allow_public_invocation ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "invoker_members" {
  for_each = { for index, member in var.invoker_members : index => member }

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = each.value
}
