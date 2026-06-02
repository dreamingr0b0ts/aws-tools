# Policy-as-code gate, evaluated against `terraform show -json <plan>`.
# Each `deny` rule blocks the deploy and prints a clear, actionable message.
package main

import rego.v1

# --- Organisation policy: required tags on every taggable resource ---
# Off-the-shelf scanners don't know your taxonomy; this is the custom part.
required_tags := {"owner", "environment", "cost-center"}

deny contains msg if {
	rc := input.resource_changes[_]
	rc.change.actions[_] != "delete"
	tags := rc.change.after.tags_all # only resources that support tags
	key := required_tags[_]
	not tags[key]
	msg := sprintf("%s is missing required tag '%s'", [rc.address, key])
}

# --- Security baseline: S3 buckets must have server-side encryption ---
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_s3_bucket"
	bucket := rc.change.after.bucket
	not bucket_encrypted(bucket)
	msg := sprintf("%s (bucket %q) has no server-side encryption", [rc.address, bucket])
}

bucket_encrypted(bucket) if {
	e := input.resource_changes[_]
	e.type == "aws_s3_bucket_server_side_encryption_configuration"
	e.change.after.bucket == bucket
}

# --- Security baseline: S3 buckets must fully block public access ---
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_s3_bucket"
	bucket := rc.change.after.bucket
	not public_access_blocked(bucket)
	msg := sprintf("%s (bucket %q) is missing a fully-enabled public access block", [rc.address, bucket])
}

public_access_blocked(bucket) if {
	p := input.resource_changes[_]
	p.type == "aws_s3_bucket_public_access_block"
	p.change.after.bucket == bucket
	p.change.after.block_public_acls == true
	p.change.after.ignore_public_acls == true
	p.change.after.block_public_policy == true
	p.change.after.restrict_public_buckets == true
}

# --- Security baseline: no security group open to the whole internet ---
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_security_group"
	ingress := rc.change.after.ingress[_]
	"0.0.0.0/0" in ingress.cidr_blocks
	msg := sprintf("%s allows ingress from 0.0.0.0/0 on port %v", [rc.address, ingress.from_port])
}
