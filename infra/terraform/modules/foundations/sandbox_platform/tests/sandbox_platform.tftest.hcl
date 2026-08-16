mock_provider "google" {}

run "creates_only_destroyable_sandbox_platform_resources" {
  command = plan

  variables {
    project_id    = "memory-director-sandbox"
    region        = "australia-southeast1"
    resource_name = "memory-director-sandbox"
  }

  assert {
    condition     = output.artifact_repository_id == "memory-director-sandbox"
    error_message = "The platform must expose its Artifact Registry repository."
  }

  assert {
    condition     = output.media_bucket_name == "memory-director-sandbox-media"
    error_message = "The platform must use its private media bucket naming contract."
  }

  assert {
    condition     = toset(output.secret_ids) == toset(["clickhouse-credentials", "gemini-runtime-config"])
    error_message = "The platform may create only secret containers, never secret values."
  }

  assert {
    condition     = output.runtime_service_account_email == "memory-director-runtime@memory-director-sandbox.iam.gserviceaccount.com"
    error_message = "The platform must expose the no-key Cloud Run runtime identity."
  }
}
