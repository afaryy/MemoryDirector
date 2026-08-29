mock_provider "google" {}

run "grants_only_the_required_public_edge_compute_roles" {
  command = plan

  variables {
    project_config     = "../../projects/config/memory-director.json"
    environment_config = "../../projects/config/sandbox.json"
  }

  assert {
    condition = toset([
      for role in var.project_roles : role
      if startswith(role, "roles/compute.")
      ]) == toset([
      "roles/compute.loadBalancerAdmin",
      "roles/compute.networkAdmin",
    ])
    error_message = "The GitHub Terraform deployer may receive only the two scoped Compute roles required to manage the public load balancer."
  }
}
