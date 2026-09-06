mock_provider "google" {}

run "creates_only_destroyable_sandbox_platform_resources" {
  command = plan

  variables {
    project_id    = "memory-director-sandbox-505708"
    region        = "australia-southeast1"
    resource_name = "memory-director-sandbox"
  }

  assert {
    condition     = output.artifact_repository_id == "memory-director-sandbox"
    error_message = "The platform must expose its Artifact Registry repository."
  }

  assert {
    condition     = output.media_bucket_name == "memory-director-sandbox-505708-media"
    error_message = "The platform must derive its globally unique private media bucket name from the project ID."
  }

  assert {
    condition     = toset(output.secret_ids) == toset(["clickhouse-credentials", "clickhouse-event-writer-credentials", "clickhouse-migration-credentials", "gemini-runtime-config"])
    error_message = "The platform must create only runtime, migration, and event-writer secret containers, never secret values."
  }

  assert {
    condition     = output.runtime_service_account_email == "memory-director-runtime@memory-director-sandbox-505708.iam.gserviceaccount.com"
    error_message = "The platform must expose the no-key Cloud Run runtime identity."
  }
}

run "plans_cross_project_mcp_secret_reference" {
  command = plan

  variables {
    project_id            = "example-project"
    region                = "australia-southeast1"
    resource_name         = "memory-director-sandbox"
    enable_mcp            = true
    mcp_secret_project_id = "memory-director"
  }

  assert {
    condition     = output.runtime_service_account_email == "memory-director-runtime@example-project.iam.gserviceaccount.com"
    error_message = "Cross-project MCP secrets must still use the platform runtime identity."
  }
}
