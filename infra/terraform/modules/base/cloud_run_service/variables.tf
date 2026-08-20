variable "project_id" { type = string }
variable "name" { type = string }
variable "region" { type = string }
variable "image" { type = string }
variable "service_account_email" { type = string }
variable "container_port" { type = number }

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "ingress" {
  type    = string
  default = "INGRESS_TRAFFIC_ALL"
}

variable "max_instance_count" {
  type    = number
  default = 3
}

variable "allow_public_invocation" {
  type    = bool
  default = true
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "secret_environment_variables" {
  type = map(object({
    secret  = string
    version = optional(string, "latest")
  }))
  default = {}
}

variable "command" {
  type    = list(string)
  default = null
}

variable "args" {
  type    = list(string)
  default = null
}

variable "invoker_members" {
  type    = list(string)
  default = []
}
