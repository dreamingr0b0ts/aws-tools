import hashlib

import boto3
from moto import mock_aws

import s3_backup

REGION = "us-east-1"


def test_md5_matches_hashlib(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"hello world")
    assert s3_backup.md5(f) == hashlib.md5(b"hello world").hexdigest()


def test_iter_files_yields_relative_posix_keys(tmp_path):
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("a")
    (root / "sub" / "b.txt").write_text("b")
    pairs = dict((rel, p) for p, rel in s3_backup.iter_files([str(root)]))
    assert set(pairs) == {"docs/a.txt", "docs/sub/b.txt"}


def test_iter_files_skips_missing(tmp_path, capsys):
    missing = tmp_path / "nope"
    assert list(s3_backup.iter_files([str(missing)])) == []
    assert "skip missing" in capsys.readouterr().out


def test_changed_true_when_absent_then_false_after_upload(tmp_path):
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket="my-backup-bucket")
        digest = "abc123"
        assert s3_backup.changed(s3, "my-backup-bucket", "k", digest) is True
        s3.put_object(Bucket="my-backup-bucket", Key="k", Body=b"x", Metadata={"md5": digest})
        assert s3_backup.changed(s3, "my-backup-bucket", "k", digest) is False
        assert s3_backup.changed(s3, "my-backup-bucket", "k", "different") is True
