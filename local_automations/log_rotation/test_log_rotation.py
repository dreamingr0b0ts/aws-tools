import gzip
import os
import time

import log_rotation


def _make(path, name, age_days, content=b"x" * 100):
    p = path / name
    p.write_bytes(content)
    t = time.time() - age_days * 86400
    os.utime(p, (t, t))
    return p


def test_find_discovers_logs_and_gz(tmp_path):
    _make(tmp_path, "a.log", 1)
    _make(tmp_path, "b.log.gz", 1)
    (tmp_path / "ignore.txt").write_text("nope")
    found = {f.name for f in log_rotation.find([str(tmp_path)], "*.log", False)}
    assert found == {"a.log", "b.log.gz"}


def test_find_skips_non_directory(tmp_path):
    assert list(log_rotation.find([str(tmp_path / "nope")], "*.log", False)) == []


def test_compress_creates_gz_and_preserves_mtime(tmp_path):
    p = _make(tmp_path, "app.log", 10)
    mtime = p.stat().st_mtime
    log_rotation.compress(p)
    gz = tmp_path / "app.log.gz"
    assert gz.exists() and not p.exists()
    assert abs(gz.stat().st_mtime - mtime) < 1  # mtime preserved for future cleanup
    with gzip.open(gz, "rb") as fh:
        assert fh.read() == b"x" * 100
