variable "project_id" {
  type        = string
  description = "Google Cloud project that owns the Terraform state backend."
}

variable "bucket_name" {
  type        = string
  description = "Globally unique state bucket name. Do not rename after state migration."
}

variable "location" {
  type        = string
  description = "Google Cloud location for state storage."
}

variable "labels" {
  type        = map(string)
  description = "Labels applied to the state bucket."
  default     = {}
}
