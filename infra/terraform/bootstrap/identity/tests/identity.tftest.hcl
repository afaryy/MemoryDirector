mock_provider "google" {}

run "grants_public_edge_roles_to_the_terraform_operator" {
  command = plan

  variables {
    project_config     = "../../projects/config/memory-director.json"
    environment_config = "../../projects/config/sandbox.json"
  }

  assert {
    condition     = contains(var.project_roles, "roles/compute.loadBalancerAdmin") && contains(var.project_roles, "roles/compute.networkAdmin") && contains(var.project_roles, "roles/compute.securityAdmin")
    error_message = "The Terraform operator needs dedicated load-balancer, network, and Cloud Armor security administration roles."
  }
}

run "grants_custom_role_administration_to_the_terraform_operator" {
  command = plan

  variables {
    project_config     = "../../projects/config/memory-director.json"
    environment_config = "../../projects/config/sandbox.json"
  }

  assert {
    condition     = contains(var.project_roles, "roles/iam.roleAdmin")
    error_message = "The Terraform operator must be able to manage the platform custom role."
  }
}

run "grants_firestore_provisioning_to_the_terraform_operator" {
  command = plan

  variables {
    project_config     = "../../projects/config/memory-director.json"
    environment_config = "../../projects/config/sandbox.json"
  }

  assert {
    condition     = contains(var.project_roles, "roles/datastore.owner")
    error_message = "The Terraform operator needs datastore.databases.create to provision the Firestore database."
  }
}
