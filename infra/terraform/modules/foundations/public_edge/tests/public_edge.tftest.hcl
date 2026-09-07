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

run "attaches_one_rate_limit_policy_to_both_public_backends" {
  command = plan

  override_resource {
    target          = google_compute_security_policy.edge
    override_during = plan
    values = {
      id = "projects/memory-director-505708/global/securityPolicies/memory-director-sandbox-edge-policy"
    }
  }

  variables {
    project_id         = "memory-director-505708"
    region             = "australia-southeast1"
    name_prefix        = "memory-director-sandbox"
    apex_domain        = "memorydirector.com"
    cloudflare_zone_id = "d963f645b3ea1a7b68611369f90cc276"
    rate_limits = {
      edge_requests_per_minute_per_ip      = 120
      api_requests_per_minute_per_ip       = 30
      film_requests_per_ten_minutes_per_ip = 5
      ban_seconds                          = 3600
      exceed_status_code                   = 429
    }
  }

  assert {
    condition     = output.api_security_policy == output.web_security_policy && output.api_security_policy != null
    error_message = "Both public backends must share the reviewed Cloud Armor policy."
  }

  assert {
    condition     = output.rate_limit_priorities == { film = 100, api = 200, edge = 300, allow = 2147483647 }
    error_message = "Costly routes must be evaluated before broader API and edge limits."
  }

  assert {
    condition = one([
      for rule in google_compute_security_policy.edge.rule : one(one(rule.match).expr).expression
      if rule.priority == 100
      ]) == join(" || ", [
      "request.path.startsWith('/api/usage/admissions')",
      "request.path.startsWith('/api/renders/export')",
      "request.path.startsWith('/api/memory-songs')",
    ])
    error_message = "Costly-route matching must use Cloud Armor-compatible path predicates without regex capture groups."
  }
}
