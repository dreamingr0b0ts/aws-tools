#!/usr/bin/env python3
"""Create EBS + RDS snapshots for tagged resources and prune old ones.

Selects resources tagged <tag-key>=<tag-value> (default backup=true), snapshots
them, then deletes previously tool-created snapshots older than the retention
window.

Safety: only snapshots created by this tool are ever pruned. EBS snapshots are
marked with the tag 'auto-snapshot=1'; RDS snapshots use the identifier prefix
'auto-'. Anything else is left untouched.

DRY-RUN by default. Pass --run to actually create and delete snapshots.
"""
import argparse
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

MARKER = "auto-snapshot"   # tag key set on EBS snapshots we create
RDS_PREFIX = "auto"        # identifier prefix on RDS snapshots we create


def all_regions():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def backup_ebs(ec2, tag_key, tag_value, run, out):
    vols = ec2.describe_volumes(
        Filters=[{"Name": f"tag:{tag_key}", "Values": [tag_value]}])["Volumes"]
    for v in vols:
        vid = v["VolumeId"]
        out.append(f"  EBS snapshot of {vid}")
        if run:
            ec2.create_snapshot(
                VolumeId=vid,
                Description=f"auto {vid} {stamp()}",
                TagSpecifications=[{
                    "ResourceType": "snapshot",
                    "Tags": [{"Key": MARKER, "Value": "1"},
                             {"Key": "source-volume", "Value": vid}],
                }])
            out.append("    -> created")


def prune_ebs(ec2, cutoff, run, out):
    snaps = ec2.describe_snapshots(
        OwnerIds=["self"],
        Filters=[{"Name": f"tag:{MARKER}", "Values": ["1"]}])["Snapshots"]
    for s in snaps:
        if s["StartTime"] < cutoff:
            out.append(f"  prune EBS snapshot {s['SnapshotId']} ({s['StartTime'].date()})")
            if run:
                ec2.delete_snapshot(SnapshotId=s["SnapshotId"])
                out.append("    -> deleted")


def backup_rds(rds, tag_key, tag_value, run, out):
    for db in rds.describe_db_instances()["DBInstances"]:
        tags = {t["Key"]: t["Value"] for t in
                rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])["TagList"]}
        if tags.get(tag_key) != tag_value:
            continue
        dbid = db["DBInstanceIdentifier"]
        snap_id = f"{RDS_PREFIX}-{dbid}-{stamp()}"
        out.append(f"  RDS snapshot of {dbid} -> {snap_id}")
        if run:
            rds.create_db_snapshot(
                DBInstanceIdentifier=dbid, DBSnapshotIdentifier=snap_id,
                Tags=[{"Key": MARKER, "Value": "1"}])
            out.append("    -> created")


def prune_rds(rds, cutoff, run, out):
    for s in rds.describe_db_snapshots(SnapshotType="manual")["DBSnapshots"]:
        if s["DBSnapshotIdentifier"].startswith(RDS_PREFIX + "-") \
                and s["SnapshotCreateTime"] < cutoff:
            sid = s["DBSnapshotIdentifier"]
            out.append(f"  prune RDS snapshot {sid} ({s['SnapshotCreateTime'].date()})")
            if run:
                rds.delete_db_snapshot(DBSnapshotIdentifier=sid)
                out.append("    -> deleted")


def main():
    p = argparse.ArgumentParser(
        description="Schedule EBS/RDS snapshots with retention pruning.")
    p.add_argument("--run", action="store_true",
                   help="Actually create/delete snapshots (default: dry-run).")
    p.add_argument("--retention-days", type=int, default=7,
                   help="Delete tool-created snapshots older than this (default 7).")
    p.add_argument("--tag-key", default="backup",
                   help="Selection tag key (default: backup).")
    p.add_argument("--tag-value", default="true",
                   help="Selection tag value (default: true).")
    p.add_argument("--regions", nargs="*",
                   help="Regions to operate in (default: all enabled regions).")
    args = p.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.retention_days)
    mode = "RUN" if args.run else "DRY-RUN"
    print(f"=== Snapshot scheduler [{mode}] | select {args.tag_key}={args.tag_value} "
          f"| retention {args.retention_days}d ===\n")

    for region in args.regions or all_regions():
        ec2 = boto3.client("ec2", region_name=region)
        rds = boto3.client("rds", region_name=region)
        out = []
        try:
            backup_ebs(ec2, args.tag_key, args.tag_value, args.run, out)
            prune_ebs(ec2, cutoff, args.run, out)
            backup_rds(rds, args.tag_key, args.tag_value, args.run, out)
            prune_rds(rds, cutoff, args.run, out)
        except ClientError as e:
            out.append(f"  skipped: {e.response['Error']['Code']}")
        if out:
            print(f"[{region}]")
            print("\n".join(out))
            print()


if __name__ == "__main__":
    main()
