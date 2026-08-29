mock_provider "google" {}

run "grants_public_edge_roles_to_the_terraform_operator" {
  command = plan

  variables {
    project_config     = "../../projects/config/memory-director.json"
    environment_config = "../../projects/config/sandbox.json"
  }

  assert {
    condition     = contains(var.project_roles, "roles/compute.loadBalancerAdmin") && contains(var.project_roles, "roles/compute.networkAdmin")
    error_message = "The Terraform operator needs dedicated load-balancer and network administration roles."
  }
}
