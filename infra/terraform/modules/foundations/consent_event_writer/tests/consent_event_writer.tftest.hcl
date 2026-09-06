mock_provider "google" {}

run "allows_authenticated_runtime_invocation" {
  command = plan

  variables {
    project_id                        = "memory-director-505708"
    region                            = "australia-southeast1"
    resource_name                     = "memory-director-sandbox"
    image                             = "australia-southeast1-docker.pkg.dev/memory-director-505708/memory-director/consent-writer:test"
    api_runtime_service_account_email = "memory-director-runtime@memory-director-505708.iam.gserviceaccount.com"
    writer_secret                     = "clickhouse-event-writer-credentials"
  }

  assert {
    condition     = module.service.ingress == "INGRESS_TRAFFIC_ALL"
    error_message = "The IAM-protected writer must be routable from Cloud Run without requiring a VPC connector."
  }
}
