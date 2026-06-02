# A configuration that breaks every policy on purpose, so the gate blocks it:
# no encryption, no public-access block, security group open to the world,
# and missing the required `environment` and `cost-center` tags.
name         = "demo"
bucket_name  = "demo-violation-bucket-0001"
ingress_cidr = "0.0.0.0/0"

enable_encryption          = false
enable_public_access_block = false

tags = {
  owner = "platform-team"
}
