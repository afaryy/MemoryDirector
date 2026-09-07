output "name" { value = google_cloud_run_v2_service.this.name }
output "uri" { value = google_cloud_run_v2_service.this.uri }
output "memory" { value = var.memory }
output "ingress" { value = var.ingress }
output "min_instance_count" { value = var.min_instance_count }
output "max_instance_count" { value = var.max_instance_count }
output "container_concurrency" { value = var.container_concurrency }
