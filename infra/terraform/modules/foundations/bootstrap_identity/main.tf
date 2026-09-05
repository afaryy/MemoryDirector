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
  required_services = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])
}

resource "google_project_service" "identity" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "github_oidc" {
  source = "../../base/github_oidc_provider"

  project_id          = var.project_id
  pool_id             = "github-actions"
  github_repositories = var.github_repositories
  allowed_ref         = var.allowed_ref
  environment         = var.environment

  depends_on = [google_project_service.identity]
}

module "terraform_deployer" {
  source = "../../base/service_account"

  project_id   = var.project_id
  account_id   = var.service_account_id
  display_name = "Memory Director sandbox Terraform deployer"
  description  = "Short-lived GitHub OIDC identity for Terraform in ${var.environment}."

  depends_on = [google_project_service.identity]
}

resource "google_service_account_iam_member" "github_workload_identity_user" {
  for_each           = var.github_repositories
  service_account_id = module.terraform_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${module.github_oidc.name}/attribute.repository/${each.value}"
}

moved {
  from = google_service_account_iam_member.github_workload_identity_user
  to   = google_service_account_iam_member.github_workload_identity_user["afaryy/MemoryDirector"]
}

resource "google_project_iam_member" "terraform_deployer" {
  for_each = var.project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${module.terraform_deployer.email}"
}
