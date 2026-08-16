variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "service" {
  type = string
  validation {
    condition     = contains(["api", "web", "all"], var.service)
    error_message = "service must be api, web, or all."
  }
}
variable "api_base_url" {
  type    = string
  default = null
}
