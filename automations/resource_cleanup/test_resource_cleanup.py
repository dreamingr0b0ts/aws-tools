import boto3
import pytest
from moto import mock_aws

import resource_cleanup

REGION = "us-east-1"


@pytest.fixture
def ec2():
    with mock_aws():
        yield boto3.client("ec2", region_name=REGION)


def test_unattached_volume_detected(ec2):
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=8)
    assert len(resource_cleanup.find_unattached_volumes(ec2)) == 1


def test_unused_eip_detected(ec2):
    ec2.allocate_address(Domain="vpc")
    assert len(resource_cleanup.find_unused_eips(ec2)) == 1


def test_no_findings_when_empty(ec2):
    assert resource_cleanup.find_unattached_volumes(ec2) == []
    assert resource_cleanup.find_unused_eips(ec2) == []
