# A configuration that satisfies every policy: encrypted, non-public,
# locked-down security group, and all required tags present.
name         = "demo"
bucket_name  = "demo-compliant-bucket-0001"
ingress_cidr = "10.0.0.0/16"

enable_encryption          = true
enable_public_access_block = true

tags = {
  owner         = "platform-team"
  environment   = "dev"
  "cost-center" = "1234"
}
