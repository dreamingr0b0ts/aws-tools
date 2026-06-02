import boto3
import pytest
from moto import mock_aws

import s3_hygiene

REGION = "us-east-1"


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket="my-test-bucket")
        yield client


def test_new_bucket_lacks_lifecycle(s3):
    assert s3_hygiene.lacks_lifecycle(s3, "my-test-bucket") is True


def test_new_bucket_not_public(s3):
    assert s3_hygiene.is_public(s3, "my-test-bucket") is False


def test_encryption_detection(s3):
    assert s3_hygiene.is_unencrypted(s3, "my-test-bucket") is True
    s3.put_bucket_encryption(
        Bucket="my-test-bucket",
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    assert s3_hygiene.is_unencrypted(s3, "my-test-bucket") is False
