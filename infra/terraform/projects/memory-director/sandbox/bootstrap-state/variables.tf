variable "project_id" {
  type        = string
  description = "Google Cloud project ID for the Memory Director sandbox."
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique, long-lived GCS bucket name for Terraform state."
}

variable "location" {
  type        = string
  description = "Google Cloud location for the state bucket."
  default     = "australia-southeast1"
}
