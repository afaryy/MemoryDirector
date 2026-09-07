variable "project_id" { type = string }
variable "bucket_name" { type = string }
variable "location" { type = string }
variable "force_destroy" { type = bool }
variable "labels" { type = map(string) }

variable "lifecycle_rules" {
  type = list(object({
    action   = string
    age_days = number
    prefix   = string
  }))
  default = []
}
