variable "project_id" {
  type        = string
  description = "Google Cloud project that owns the Terraform state bucket."
}

variable "bucket_name" {
  type        = string
  description = "Globally unique, immutable name for the Terraform state bucket."
}

variable "location" {
  type        = string
  description = "Google Cloud location for the Terraform state bucket."
}

variable "labels" {
  type        = map(string)
  description = "Resource labels applied to the Terraform state bucket."
  default     = {}
}
