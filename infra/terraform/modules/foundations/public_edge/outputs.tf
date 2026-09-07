output "edge_ip" { value = google_compute_global_address.edge.address }
output "apex_url" { value = "https://${var.apex_domain}" }
output "certificate_name" { value = google_compute_managed_ssl_certificate.edge.name }
output "api_neg_id" { value = google_compute_region_network_endpoint_group.api.id }
output "web_neg_id" { value = google_compute_region_network_endpoint_group.web.id }
output "url_map_name" { value = google_compute_url_map.https.name }
output "api_path_prefix_rewrite" { value = "/" }
output "apex_dns_proxied" { value = cloudflare_dns_record.apex.proxied }
output "www_dns_proxied" { value = cloudflare_dns_record.www.proxied }
output "api_security_policy" { value = google_compute_backend_service.api.security_policy }
output "web_security_policy" { value = google_compute_backend_service.web.security_policy }
output "rate_limit_priorities" { value = { film = 100, api = 200, edge = 300, allow = 2147483647 } }
