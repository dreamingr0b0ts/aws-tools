#!/usr/bin/env python3
"""Report S3 buckets that are public, unencrypted, or lack a lifecycle policy.

Read-only: lists every bucket in the account and flags hygiene issues. Each
bucket is queried against its own region to avoid redirect errors.
"""
import boto3
from botocore.exceptions import ClientError

PUBLIC_GROUPS = ("AllUsers", "AuthenticatedUsers")
PAB_KEYS = ("BlockPublicAcls", "IgnorePublicAcls",
            "BlockPublicPolicy", "RestrictPublicBuckets")


def bucket_region(s3, bucket):
    return s3.get_bucket_location(Bucket=bucket)["LocationConstraint"] or "us-east-1"


def is_public(s3, bucket):
    try:  # A full Public Access Block makes the bucket non-public regardless.
        cfg = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
        if all(cfg.get(k) for k in PAB_KEYS):
            return False
    except ClientError:
        pass
    try:
        if s3.get_bucket_policy_status(Bucket=bucket)["PolicyStatus"].get("IsPublic"):
            return True
    except ClientError:
        pass
    try:
        for grant in s3.get_bucket_acl(Bucket=bucket)["Grants"]:
            if any(g in grant["Grantee"].get("URI", "") for g in PUBLIC_GROUPS):
                return True
    except ClientError:
        pass
    return False


def is_unencrypted(s3, bucket):
    try:
        s3.get_bucket_encryption(Bucket=bucket)
        return False
    except ClientError as e:
        return e.response["Error"]["Code"] == \
            "ServerSideEncryptionConfigurationNotFoundError"


def lacks_lifecycle(s3, bucket):
    try:
        s3.get_bucket_lifecycle_configuration(Bucket=bucket)
        return False
    except ClientError as e:
        return e.response["Error"]["Code"] == "NoSuchLifecycleConfiguration"


def main():
    s3 = boto3.client("s3")
    clients = {}
    buckets = s3.list_buckets()["Buckets"]
    print(f"=== S3 hygiene | {len(buckets)} bucket(s) ===\n")
    flagged = 0
    for b in buckets:
        name = b["Name"]
        try:
            region = bucket_region(s3, name)
            c = clients.setdefault(region, boto3.client("s3", region_name=region))
            issues = []
            if is_public(c, name):
                issues.append("PUBLIC")
            if is_unencrypted(c, name):
                issues.append("unencrypted")
            if lacks_lifecycle(c, name):
                issues.append("no-lifecycle")
        except ClientError as e:
            print(f"{name}: skipped ({e.response['Error']['Code']})")
            continue
        if issues:
            flagged += 1
            print(f"{name} [{region}]: {', '.join(issues)}")
    print(f"\n{flagged} of {len(buckets)} bucket(s) flagged.")


if __name__ == "__main__":
    main()
