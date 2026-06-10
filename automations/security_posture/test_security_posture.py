import boto3
from moto import mock_aws

import security_posture

REGION = "us-east-1"


def _open_sg(ec2, cidr="0.0.0.0/0", proto="tcp", from_port=22, to_port=22):
    sg = ec2.create_security_group(GroupName="open", Description="open")
    ec2.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[
            {
                "IpProtocol": proto,
                "FromPort": from_port,
                "ToPort": to_port,
                "IpRanges": [{"CidrIp": cidr}],
            }
        ],
    )
    return sg["GroupId"]


def test_open_sg_flagged():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name=REGION)
        gid = _open_sg(ec2)
        flagged = security_posture.open_security_groups(REGION)
        ids = {g[0] for g in flagged}
        assert gid in ids
        opens = next(opens for g, _, opens in flagged if g == gid)
        assert "tcp/22" in opens


def test_restricted_sg_not_flagged():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name=REGION)
        _open_sg(ec2, cidr="10.0.0.0/8")
        flagged = security_posture.open_security_groups(REGION)
        # The default VPC SG has no ingress; our 10/8 rule isn't world-open.
        assert all("tcp/22" not in opens for _, _, opens in flagged)
