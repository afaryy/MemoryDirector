mock_provider "google" {}

run "creates_public_api_and_web_services_from_immutable_images" {
  command = plan

  variables {
    project_id   = "memory-director-sandbox"
    region       = "australia-southeast1"
    name_prefix  = "memory-director-sandbox"
    api_image    = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    web_image    = "example.invalid/web@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    service      = "all"
    api_base_url = null
  }

  assert {
    condition     = output.runtime_service_account_email == "memory-director-runtime@memory-director-sandbox.iam.gserviceaccount.com"
    error_message = "Both app services must use the no-key runtime identity."
  }

  assert {
    condition     = output.service == "all"
    error_message = "The default app foundation state must manage both services."
  }

  assert {
    condition     = startswith(output.api_image, "example.invalid/api@sha256:") && startswith(output.web_image, "example.invalid/web@sha256:")
    error_message = "App services must be configured with immutable image references."
  }
}
