#!/usr/bin/env python3
"""Find (and optionally delete) unused/idle AWS resources to cut cost.

Detects: unattached EBS volumes, snapshots older than --days, unused Elastic
IPs, and idle load balancers (no registered targets/instances).

DRY-RUN by default (report only). Pass --delete to actually remove resources.
Deletion is irreversible.
"""

import argparse
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError


def all_regions():
    # Intentionally duplicated across tools: each script is self-contained
    # (its own folder + venv) so it can be copied/run in isolation.
    ec2 = boto3.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def find_unattached_volumes(ec2):
    vols = [
        v
        for page in ec2.get_paginator("describe_volumes").paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )
        for v in page["Volumes"]
    ]
    return [(v["VolumeId"], f"{v['Size']}GiB {v['VolumeType']}") for v in vols]


def find_old_snapshots(ec2, days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    snaps = [
        s
        for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"])
        for s in page["Snapshots"]
    ]
    return [
        (s["SnapshotId"], f"{s['StartTime'].date()} {s.get('VolumeSize', '?')}GiB")
        for s in snaps
        if s["StartTime"] < cutoff
    ]


def find_unused_eips(ec2):
    # describe_addresses is not paginated by the AWS API (returns all at once).
    addrs = ec2.describe_addresses()["Addresses"]
    return [(a["AllocationId"], a["PublicIp"]) for a in addrs if "AssociationId" not in a]


def find_idle_load_balancers(region):
    idle = []
    elb = boto3.client("elb", region_name=region)
    for page in elb.get_paginator("describe_load_balancers").paginate():
        for lb in page["LoadBalancerDescriptions"]:
            if not lb["Instances"]:
                idle.append(("classic", lb["LoadBalancerName"], lb["LoadBalancerName"]))
    elbv2 = boto3.client("elbv2", region_name=region)
    for page in elbv2.get_paginator("describe_load_balancers").paginate():
        for lb in page["LoadBalancers"]:
            arn = lb["LoadBalancerArn"]
            target_groups = [
                tg
                for tg_page in elbv2.get_paginator("describe_target_groups").paginate(
                    LoadBalancerArn=arn
                )
                for tg in tg_page["TargetGroups"]
            ]
            registered = sum(
                len(
                    elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])[
                        "TargetHealthDescriptions"
                    ]
                )
                for tg in target_groups
            )
            if registered == 0:
                idle.append(("v2", lb["LoadBalancerName"], arn))
    return idle


def scan_region(region, days, delete):
    ec2 = boto3.client("ec2", region_name=region)
    actions = [
        (
            "unattached volume",
            find_unattached_volumes(ec2),
            lambda ref: ec2.delete_volume(VolumeId=ref),
            "deleted",
        ),
        (
            "old snapshot",
            find_old_snapshots(ec2, days),
            lambda ref: ec2.delete_snapshot(SnapshotId=ref),
            "deleted",
        ),
        (
            "unused EIP",
            find_unused_eips(ec2),
            lambda ref: ec2.release_address(AllocationId=ref),
            "released",
        ),
    ]
    lbs = find_idle_load_balancers(region)
    if not any(items for _, items, _, _ in actions) and not lbs:
        return
    print(f"[{region}]")
    for label, items, deleter, verb in actions:
        for ref, desc in items:
            print(f"  {label} {ref} ({desc})")
            if delete:
                deleter(ref)
                print(f"    -> {verb}")
    for kind, name, ref in lbs:
        print(f"  idle load balancer {name} ({kind})")
        if delete:
            if kind == "classic":
                boto3.client("elb", region_name=region).delete_load_balancer(LoadBalancerName=ref)
            else:
                boto3.client("elbv2", region_name=region).delete_load_balancer(LoadBalancerArn=ref)
            print("    -> deleted")
    print()


def main():
    p = argparse.ArgumentParser(description="Report or delete unused AWS resources.")
    p.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete flagged resources (default: dry-run).",
    )
    p.add_argument(
        "--days", type=int, default=90, help="Snapshot age threshold in days (default 90)."
    )
    p.add_argument("--regions", nargs="*", help="Regions to scan (default: all enabled regions).")
    args = p.parse_args()

    mode = "DELETE" if args.delete else "DRY-RUN"
    print(f"=== Resource cleanup [{mode}] | snapshot age > {args.days}d ===\n")
    for region in args.regions or all_regions():
        try:
            scan_region(region, args.days, args.delete)
        except ClientError as e:
            print(f"[{region}] skipped: {e.response['Error']['Code']}\n")


if __name__ == "__main__":
    main()
