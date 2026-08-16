mock_provider "google" {}

run "creates_a_private_versioned_state_bucket" {
  command = plan

  variables {
    project_id  = "memory-director-sandbox"
    bucket_name = "memory-director-sandbox-tfstate"
    location    = "australia-southeast1"
  }

  assert {
    condition     = output.state_bucket_name == "memory-director-sandbox-tfstate"
    error_message = "The bootstrap state bucket must use the supplied globally unique name."
  }

  assert {
    condition     = output.uniform_bucket_level_access
    error_message = "Terraform state must use uniform bucket-level access."
  }

  assert {
    condition     = output.public_access_prevention == "enforced"
    error_message = "Terraform state must never allow public access."
  }

  assert {
    condition     = output.versioning_enabled
    error_message = "Terraform state bucket object versioning must be enabled."
  }
}
