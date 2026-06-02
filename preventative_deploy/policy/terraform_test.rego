# Unit tests for the policies, runnable with `conftest verify`.
# Policies are tested in isolation against synthetic plan fragments -- no
# Terraform or AWS required.
package main

import rego.v1

# A bucket missing required tags must be denied.
test_missing_tag_denied if {
	count(deny) > 0 with input as {"resource_changes": [{
		"address": "aws_s3_bucket.x",
		"type": "aws_s3_bucket",
		"change": {"actions": ["create"], "after": {"bucket": "b", "tags_all": {"owner": "x"}}},
	}]}
}

# A security group open to the world must be denied.
test_open_sg_denied if {
	count(deny) > 0 with input as {"resource_changes": [{
		"address": "aws_security_group.x",
		"type": "aws_security_group",
		"change": {"actions": ["create"], "after": {
			"tags_all": {"owner": "o", "environment": "e", "cost-center": "c"},
			"ingress": [{"from_port": 22, "cidr_blocks": ["0.0.0.0/0"]}],
		}},
	}]}
}

# A fully-compliant plan must produce zero denials.
test_compliant_allowed if {
	count(deny) == 0 with input as {"resource_changes": [
		{
			"address": "aws_s3_bucket.x",
			"type": "aws_s3_bucket",
			"change": {"actions": ["create"], "after": {
				"bucket": "b",
				"tags_all": {"owner": "o", "environment": "e", "cost-center": "c"},
			}},
		},
		{
			"address": "aws_s3_bucket_server_side_encryption_configuration.x",
			"type": "aws_s3_bucket_server_side_encryption_configuration",
			"change": {"actions": ["create"], "after": {"bucket": "b"}},
		},
		{
			"address": "aws_s3_bucket_public_access_block.x",
			"type": "aws_s3_bucket_public_access_block",
			"change": {"actions": ["create"], "after": {
				"bucket": "b",
				"block_public_acls": true,
				"ignore_public_acls": true,
				"block_public_policy": true,
				"restrict_public_buckets": true,
			}},
		},
	]}
}
