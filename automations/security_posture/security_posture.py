#!/usr/bin/env python3
"""Report basic AWS security-posture issues (read-only):

* Whether the root account has MFA enabled
* IAM users without an MFA device
* Active access keys older than --days (default 90)
* Security groups allowing inbound traffic from anywhere (0.0.0.0/0 or ::/0)
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


def iam_findings(days):
    iam = boto3.client("iam")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    root_mfa = iam.get_account_summary()["SummaryMap"].get("AccountMFAEnabled", 0) == 1
    no_mfa, old_keys = [], []
    for page in iam.get_paginator("list_users").paginate():
        for u in page["Users"]:
            name = u["UserName"]
            if not iam.list_mfa_devices(UserName=name)["MFADevices"]:
                no_mfa.append(name)
            for k in iam.list_access_keys(UserName=name)["AccessKeyMetadata"]:
                if k["Status"] == "Active" and k["CreateDate"] < cutoff:
                    age = (datetime.now(timezone.utc) - k["CreateDate"]).days
                    old_keys.append((name, k["AccessKeyId"], age))
    return root_mfa, no_mfa, old_keys


def open_security_groups(region):
    ec2 = boto3.client("ec2", region_name=region)
    flagged = []
    groups = [
        sg
        for page in ec2.get_paginator("describe_security_groups").paginate()
        for sg in page["SecurityGroups"]
    ]
    for sg in groups:
        opens = []
        for perm in sg["IpPermissions"]:
            world = any(r.get("CidrIp") == "0.0.0.0/0" for r in perm.get("IpRanges", [])) or any(
                r.get("CidrIpv6") == "::/0" for r in perm.get("Ipv6Ranges", [])
            )
            if not world:
                continue
            proto = perm.get("IpProtocol")
            if proto == "-1":
                opens.append("ALL")
            else:
                f, t = perm.get("FromPort"), perm.get("ToPort")
                opens.append(f"{proto}/{f}" if f == t else f"{proto}/{f}-{t}")
        if opens:
            flagged.append((sg["GroupId"], sg.get("GroupName", ""), opens))
    return flagged


def main():
    p = argparse.ArgumentParser(description="Report basic AWS security-posture issues.")
    p.add_argument(
        "--days", type=int, default=90, help="Active access key age threshold in days (default 90)."
    )
    p.add_argument(
        "--regions", nargs="*", help="Regions for the security-group scan (default: all enabled)."
    )
    args = p.parse_args()

    print("=== Security posture ===\n")
    root_mfa, no_mfa, old_keys = iam_findings(args.days)

    print(f"-- Root account MFA: {'enabled' if root_mfa else 'NOT ENABLED'} --")

    print(f"\n-- IAM users without MFA ({len(no_mfa)}) --")
    for name in no_mfa:
        print(f"  {name}")

    print(f"\n-- Active access keys older than {args.days}d ({len(old_keys)}) --")
    for name, kid, age in old_keys:
        print(f"  {name}: {kid} ({age}d)")

    print("\n-- Security groups open to the world (0.0.0.0/0 or ::/0) --")
    for region in args.regions or all_regions():
        try:
            flagged = open_security_groups(region)
        except ClientError as e:
            print(f"  [{region}] skipped: {e.response['Error']['Code']}")
            continue
        for gid, gname, opens in flagged:
            print(f"  [{region}] {gid} ({gname}): {', '.join(opens)}")


if __name__ == "__main__":
    main()
