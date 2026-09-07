terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

locals {
  api_service_name = coalesce(var.api_service_name, "${var.name_prefix}-api")
  web_service_name = coalesce(var.web_service_name, "${var.name_prefix}-web")
  www_domain       = "www.${var.apex_domain}"
}

resource "google_compute_region_network_endpoint_group" "api" {
  project               = var.project_id
  region                = var.region
  name                  = "${var.name_prefix}-api-neg"
  network_endpoint_type = "SERVERLESS"

  cloud_run { service = local.api_service_name }
}

resource "google_compute_region_network_endpoint_group" "web" {
  project               = var.project_id
  region                = var.region
  name                  = "${var.name_prefix}-web-neg"
  network_endpoint_type = "SERVERLESS"

  cloud_run { service = local.web_service_name }
}

resource "google_compute_backend_service" "api" {
  project               = var.project_id
  name                  = "${var.name_prefix}-api-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.edge.id

  backend { group = google_compute_region_network_endpoint_group.api.id }
}

resource "google_compute_backend_service" "web" {
  project               = var.project_id
  name                  = "${var.name_prefix}-web-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.edge.id

  backend { group = google_compute_region_network_endpoint_group.web.id }
}

resource "google_compute_security_policy" "edge" {
  project     = var.project_id
  name        = "${var.name_prefix}-edge-policy"
  description = "Layered per-IP protection for Memory Director public and generation traffic."

  rule {
    action      = "rate_based_ban"
    priority    = 100
    description = "Bound costly film export and original-song requests."
    match {
      expr {
        expression = join(" || ", [
          "request.path.startsWith('/api/usage/admissions')",
          "request.path.startsWith('/api/renders/export')",
          "request.path.startsWith('/api/memory-songs')",
        ])
      }
    }
    rate_limit_options {
      conform_action   = "allow"
      exceed_action    = "deny(${var.rate_limits.exceed_status_code})"
      enforce_on_key   = "IP"
      ban_duration_sec = var.rate_limits.ban_seconds
      rate_limit_threshold {
        count        = var.rate_limits.film_requests_per_ten_minutes_per_ip
        interval_sec = 600
      }
    }
  }

  rule {
    action      = "rate_based_ban"
    priority    = 200
    description = "Bound other API requests."
    match {
      expr {
        expression = "request.path.startsWith('/api/')"
      }
    }
    rate_limit_options {
      conform_action   = "allow"
      exceed_action    = "deny(${var.rate_limits.exceed_status_code})"
      enforce_on_key   = "IP"
      ban_duration_sec = var.rate_limits.ban_seconds
      rate_limit_threshold {
        count        = var.rate_limits.api_requests_per_minute_per_ip
        interval_sec = 60
      }
    }
  }

  rule {
    action      = "rate_based_ban"
    priority    = 300
    description = "Bound general public requests."
    match {
      expr {
        expression = "true"
      }
    }
    rate_limit_options {
      conform_action   = "allow"
      exceed_action    = "deny(${var.rate_limits.exceed_status_code})"
      enforce_on_key   = "IP"
      ban_duration_sec = var.rate_limits.ban_seconds
      rate_limit_threshold {
        count        = var.rate_limits.edge_requests_per_minute_per_ip
        interval_sec = 60
      }
    }
  }

  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Default allow after rate-limit evaluation."
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}

resource "google_compute_global_address" "edge" {
  project      = var.project_id
  name         = "${var.name_prefix}-edge-ip"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

resource "google_compute_managed_ssl_certificate" "edge" {
  project = var.project_id
  name    = "${var.name_prefix}-edge-cert"

  managed { domains = [var.apex_domain, local.www_domain] }

  lifecycle { create_before_destroy = true }
}

resource "google_compute_url_map" "https" {
  project         = var.project_id
  name            = "${var.name_prefix}-https-map"
  default_service = google_compute_backend_service.web.id

  host_rule {
    hosts        = [var.apex_domain]
    path_matcher = "apex"
  }

  host_rule {
    hosts        = [local.www_domain]
    path_matcher = "www-redirect"
  }

  path_matcher {
    name            = "apex"
    default_service = google_compute_backend_service.web.id

    route_rules {
      priority = 1
      service  = google_compute_backend_service.api.id

      match_rules { prefix_match = "${var.api_path_prefix}/" }

      route_action {
        url_rewrite { path_prefix_rewrite = "/" }
      }
    }
  }

  path_matcher {
    name = "www-redirect"

    default_url_redirect {
      host_redirect          = var.apex_domain
      https_redirect         = true
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }
}

resource "google_compute_url_map" "http_redirect" {
  project = var.project_id
  name    = "${var.name_prefix}-http-redirect-map"

  default_url_redirect {
    host_redirect          = var.apex_domain
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_https_proxy" "edge" {
  project          = var.project_id
  name             = "${var.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.edge.id]
}

resource "google_compute_target_http_proxy" "redirect" {
  project = var.project_id
  name    = "${var.name_prefix}-http-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "https" {
  project               = var.project_id
  name                  = "${var.name_prefix}-https-forwarding-rule"
  ip_address            = google_compute_global_address.edge.id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  port_range            = "443"
  target                = google_compute_target_https_proxy.edge.id
}

resource "google_compute_global_forwarding_rule" "http" {
  project               = var.project_id
  name                  = "${var.name_prefix}-http-forwarding-rule"
  ip_address            = google_compute_global_address.edge.id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
}

resource "cloudflare_dns_record" "apex" {
  zone_id = var.cloudflare_zone_id
  name    = var.apex_domain
  type    = "A"
  content = google_compute_global_address.edge.address
  ttl     = 60
  proxied = false
  comment = "Memory Director Google Cloud public edge"
}

resource "cloudflare_dns_record" "www" {
  zone_id = var.cloudflare_zone_id
  name    = "www"
  type    = "CNAME"
  content = var.apex_domain
  ttl     = 60
  proxied = false
  comment = "Memory Director www redirect via Google Cloud public edge"
}
