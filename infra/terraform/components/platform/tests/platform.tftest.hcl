mock_provider "google" {}

run "plans_base_platform_without_consent_writer_image" {
  command = plan

  variables {
    project_config              = "../../projects/config/memory-director.json"
    environment_config          = "../../projects/config/sandbox.json"
    enable_consent_event_writer = false
  }

  assert {
    condition     = output.configuration_summary.project_id == "memory-director-505708"
    error_message = "The base platform plan must target the Memory Director project without requiring a disabled writer image."
  }
}
