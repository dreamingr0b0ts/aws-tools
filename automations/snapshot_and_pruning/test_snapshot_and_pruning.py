import re

import boto3
import pytest
from moto import mock_aws

import snapshot_and_pruning as sp

REGION = "us-east-1"


def test_stamp_format():
    assert re.fullmatch(r"\d{8}-\d{6}", sp.stamp())


@pytest.fixture
def ec2():
    with mock_aws():
        yield boto3.client("ec2", region_name=REGION)


def _tagged_volume(ec2, tags):
    vol = ec2.create_volume(
        AvailabilityZone=f"{REGION}a",
        Size=8,
        TagSpecifications=[{"ResourceType": "volume", "Tags": tags}],
    )
    return vol["VolumeId"]


def _our_snapshots(ec2):
    # OwnerIds=self still returns moto's seeded public snapshots; scope to ours.
    return ec2.describe_snapshots(
        OwnerIds=["self"], Filters=[{"Name": f"tag:{sp.MARKER}", "Values": ["1"]}]
    )["Snapshots"]


def test_backup_ebs_dry_run_lists_but_creates_nothing(ec2):
    vid = _tagged_volume(ec2, [{"Key": "backup", "Value": "true"}])
    out = []
    sp.backup_ebs(ec2, "backup", "true", run=False, out=out)
    assert any(vid in line for line in out)
    assert _our_snapshots(ec2) == []


def test_backup_ebs_run_creates_marked_snapshot(ec2):
    _tagged_volume(ec2, [{"Key": "backup", "Value": "true"}])
    out = []
    sp.backup_ebs(ec2, "backup", "true", run=True, out=out)
    snaps = _our_snapshots(ec2)
    assert len(snaps) == 1
    tags = {t["Key"]: t["Value"] for t in snaps[0]["Tags"]}
    assert tags.get(sp.MARKER) == "1"


def test_backup_ebs_skips_untagged(ec2):
    _tagged_volume(ec2, [{"Key": "backup", "Value": "false"}])
    out = []
    sp.backup_ebs(ec2, "backup", "true", run=True, out=out)
    assert out == []
    assert _our_snapshots(ec2) == []
