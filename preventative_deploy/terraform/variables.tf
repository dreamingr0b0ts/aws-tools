variable "name" {
  type    = string
  default = "demo"
}

variable "bucket_name" {
  type = string
}

variable "ingress_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "enable_encryption" {
  type    = bool
  default = true
}

variable "enable_public_access_block" {
  type    = bool
  default = true
}

# Required organisation tags are supplied here and applied to every resource
# via the provider's default_tags. The policy enforces their presence.
variable "tags" {
  type = map(string)
}
