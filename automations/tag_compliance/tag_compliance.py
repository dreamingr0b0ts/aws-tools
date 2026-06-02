#!/usr/bin/env python3
"""Scan AWS resources for missing required tags and report or auto-tag them.

Uses the Resource Groups Tagging API, which covers most taggable resources
across services in a region.

Report-only by default. Pass --apply together with --set KEY=VALUE pairs to fill
in missing tags; only the missing keys are written on each resource.
"""
import argparse

import boto3
from botocore.exceptions import ClientError

DEFAULT_REQUIRED = ["owner", "environment", "cost-center"]


def all_regions():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def iter_resources(client):
    for page in client.get_paginator("get_resources").paginate():
        for r in page["ResourceTagMappingList"]:
            yield r["ResourceARN"], {t["Key"]: t["Value"] for t in r["Tags"]}


def scan_region(region, required, apply, values):
    client = boto3.client("resourcegroupstaggingapi", region_name=region)
    printed = False
    for arn, tags in iter_resources(client):
        missing = [k for k in required if k not in tags]
        if not missing:
            continue
        if not printed:
            print(f"[{region}]")
            printed = True
        print(f"  {arn}\n    missing: {', '.join(missing)}")
        if apply:
            to_set = {k: values[k] for k in missing if k in values}
            if to_set:
                client.tag_resources(ResourceARNList=[arn], Tags=to_set)
                print("    -> tagged: "
                      + ", ".join(f"{k}={v}" for k, v in to_set.items()))
    if printed:
        print()


def parse_set(pairs):
    values = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        values[key] = value
    return values


def main():
    p = argparse.ArgumentParser(description="Report or fix missing required tags.")
    p.add_argument("--required", nargs="*", default=DEFAULT_REQUIRED,
                   help=f"Required tag keys (default: {' '.join(DEFAULT_REQUIRED)}).")
    p.add_argument("--apply", action="store_true",
                   help="Write missing tags using --set values (default: report only).")
    p.add_argument("--set", nargs="*", dest="set_pairs", metavar="KEY=VALUE",
                   help="Default values for missing tags, e.g. owner=alice environment=prod.")
    p.add_argument("--regions", nargs="*",
                   help="Regions to scan (default: all enabled regions).")
    args = p.parse_args()

    values = parse_set(args.set_pairs)
    if args.apply and not values:
        p.error("--apply requires at least one --set KEY=VALUE")

    mode = "APPLY" if args.apply else "REPORT"
    print(f"=== Tag compliance [{mode}] | required: {', '.join(args.required)} ===\n")
    for region in args.regions or all_regions():
        try:
            scan_region(region, args.required, args.apply, values)
        except ClientError as e:
            print(f"[{region}] skipped: {e.response['Error']['Code']}\n")


if __name__ == "__main__":
    main()
