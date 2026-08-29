variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" { type = string }

variable "apex_domain" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+[a-z0-9]$", var.apex_domain))
    error_message = "apex_domain must be a lowercase DNS name."
  }
}

variable "cloudflare_zone_id" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.cloudflare_zone_id))
    error_message = "cloudflare_zone_id must be a 32-character lowercase hexadecimal Zone ID."
  }
}

variable "api_path_prefix" {
  type    = string
  default = "/api"
  validation {
    condition     = var.api_path_prefix == "/api"
    error_message = "api_path_prefix must be /api."
  }
}

variable "api_service_name" {
  type    = string
  default = null
}

variable "web_service_name" {
  type    = string
  default = null
}
