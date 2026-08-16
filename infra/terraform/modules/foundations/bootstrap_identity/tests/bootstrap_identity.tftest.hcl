mock_provider "google" {}

run "restricts_github_federation_to_the_sandbox_repository_and_main" {
  command = plan

  variables {
    project_id         = "memory-director-sandbox"
    github_owner       = "afaryy"
    github_repo        = "MemoryDirector"
    allowed_ref        = "refs/heads/main"
    environment        = "sandbox"
    service_account_id = "github-terraform-sandbox"
  }

  assert {
    condition     = output.github_repository == "afaryy/MemoryDirector"
    error_message = "The deployment identity must be restricted to the Memory Director repository."
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
