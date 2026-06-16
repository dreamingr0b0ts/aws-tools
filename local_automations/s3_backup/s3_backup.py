#!/usr/bin/env python3
"""Back up local folders to an S3 bucket with versioning enabled.

Only changed files are uploaded; the bucket's versioning keeps prior copies, so
you get point-in-time history automatically. Change detection compares an md5
stored in each object's metadata (robust against S3 multipart ETags).

    python3 s3_backup.py my-bucket ~/Documents ~/projects --prefix laptop
    python3 s3_backup.py my-bucket ~/Documents --dry-run
    python3 s3_backup.py my-bucket ~/Documents --create-bucket --region us-west-2
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def md5(path, chunk=1 << 20):
    # Used only for change detection, not security; the flag keeps scanners
    # (Bandit/Checkov) from flagging md5.
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def ensure_bucket(s3, bucket, region, create):
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        if not create:
            sys.exit(f"error: bucket '{bucket}' not found (pass --create-bucket to create it)")
        kwargs = {"Bucket": bucket}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kwargs)
        print(f"created bucket {bucket}")
    s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})


def changed(s3, bucket, key, digest):
    try:
        return s3.head_object(Bucket=bucket, Key=key)["Metadata"].get("md5") != digest
    except ClientError as e:
        # A genuine "not found" means the object is new -> upload it. Anything
        # else (AccessDenied, throttling, etc.) is a real problem we shouldn't
        # mask as "changed", so re-raise it.
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return True  # object not present
        raise


def iter_files(paths):
    for raw in paths:
        root = Path(raw).expanduser()
        if not root.exists():
            print(f"! skip missing path: {root}")
            continue
        base = root.parent
        for f in root.rglob("*") if root.is_dir() else [root]:
            if f.is_file():
                yield f, f.relative_to(base).as_posix()


def main():
    p = argparse.ArgumentParser(description="Back up folders to S3 with versioning.")
    p.add_argument("bucket")
    p.add_argument("paths", nargs="+", help="Folders (or files) to back up.")
    p.add_argument("--prefix", default="", help="Key prefix within the bucket.")
    p.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    p.add_argument(
        "--create-bucket",
        action="store_true",
        help="Create the bucket (with versioning) if it doesn't exist.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List candidate files locally without contacting AWS.",
    )
    args = p.parse_args()

    prefix = args.prefix.strip("/")
    s3 = None
    if not args.dry_run:
        s3 = boto3.client("s3", region_name=args.region)
        ensure_bucket(s3, args.bucket, args.region, args.create_bucket)

    uploaded = skipped = 0
    for f, rel in iter_files(args.paths):
        key = f"{prefix}/{rel}" if prefix else rel
        if args.dry_run:
            print(f"  would upload {key}")
            uploaded += 1
            continue
        digest = md5(f)
        if changed(s3, args.bucket, key, digest):
            s3.upload_file(str(f), args.bucket, key, ExtraArgs={"Metadata": {"md5": digest}})
            print(f"  uploaded {key}")
            uploaded += 1
        else:
            skipped += 1

    verb = "would upload" if args.dry_run else "uploaded"
    print(f"\n{verb} {uploaded}, skipped {skipped}.")


if __name__ == "__main__":
    main()
