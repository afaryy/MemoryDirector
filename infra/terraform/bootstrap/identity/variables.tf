variable "project_config" { type = string }
variable "environment_config" { type = string }
variable "project_roles" {
  type = set(string)
  default = [
    "roles/aiplatform.admin",
    "roles/artifactregistry.admin",
    "roles/compute.loadBalancerAdmin",
    "roles/compute.networkAdmin",
    "roles/compute.securityAdmin",
    "roles/datastore.owner",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/iam.roleAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
  ]
}
