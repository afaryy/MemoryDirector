mock_provider "google" {}

run "restricts_github_federation_to_the_sandbox_repository_and_main" {
  command = plan

  variables {
    project_id          = "memory-director-sandbox"
    github_owner        = "afaryy"
    github_repo         = "MemoryDirector"
    github_repositories = ["afaryy/MemoryDirector", "sailing-together/MemoryDirector"]
    allowed_ref         = "refs/heads/main"
    environment         = "sandbox"
    service_account_id  = "github-terraform-sandbox"
  }

  assert {
    condition     = output.github_repository == "afaryy/MemoryDirector"
    error_message = "The deployment identity must be restricted to the Memory Director repository."
  }

  assert {
    condition     = toset(output.github_repositories) == toset(["afaryy/MemoryDirector", "sailing-together/MemoryDirector"])
    error_message = "The transitional WIF policy must trust exactly the current and target Memory Director repositories."
  }

  assert {
    condition     = module.github_oidc.attribute_condition == "assertion.repository in [\"afaryy/MemoryDirector\",\"sailing-together/MemoryDirector\"] && assertion.ref == 'refs/heads/main' && assertion.environment == 'sandbox'"
    error_message = "WIF must restrict both allowed repositories to the main ref and sandbox environment."
  }

  assert {
    condition = toset(keys(google_service_account_iam_member.github_workload_identity_user)) == toset([
      "afaryy/MemoryDirector",
      "sailing-together/MemoryDirector",
    ])
    error_message = "Only the current and target repositories may impersonate the Terraform service account during the transition."
  }

  assert {
    condition     = output.allowed_ref == "refs/heads/main"
    error_message = "The deployment identity must be restricted to the approved main ref."
  }

  assert {
    condition     = output.environment == "sandbox"
    error_message = "The deployment identity must be restricted to the sandbox environment."
  }

  assert {
    condition     = output.service_account_email == "github-terraform-sandbox@memory-director-sandbox.iam.gserviceaccount.com"
    error_message = "The foundation must expose the deploy service-account identity without a key."
  }

  assert {
    condition     = toset(output.enabled_services) == toset(["iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com"])
    error_message = "WIF bootstrap must enable only the IAM and STS APIs it requires."
  }
}
