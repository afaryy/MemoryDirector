mock_provider "google" {}
mock_provider "cloudflare" {}

run "routes_api_prefix_to_api_neg_with_prefix_removed" {
  command = plan

  variables {
    project_id         = "example-project"
    region             = "australia-southeast1"
    name_prefix        = "memory-director-sandbox"
    apex_domain        = "memorydirector.com"
    cloudflare_zone_id = "d963f645b3ea1a7b68611369f90cc276"
    api_path_prefix    = "/api"
  }

  assert {
    condition     = output.api_path_prefix_rewrite == "/"
    error_message = "FastAPI must receive paths without the /api prefix."
  }

  assert {
    condition     = output.apex_dns_proxied == false && output.www_dns_proxied == false
    error_message = "DNS must be DNS-only while Google manages the certificate."
  }
}
