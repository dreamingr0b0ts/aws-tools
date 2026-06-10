import health_checks


def test_check_disk_ok_when_below_threshold(tmp_path):
    ((ok, msg),) = health_checks.check_disk([str(tmp_path)], threshold=100)
    assert ok is True
    assert "disk" in msg and "used" in msg


def test_check_disk_fails_when_threshold_zero(tmp_path):
    ((ok, _),) = health_checks.check_disk([str(tmp_path)], threshold=0)
    assert ok is False  # any usage >= 0% trips a 0 threshold


def test_check_disk_missing_path():
    ((ok, msg),) = health_checks.check_disk(["/no/such/mount/here"], threshold=90)
    assert ok is False
    assert "not found" in msg


def test_is_running_false_for_bogus_process():
    assert health_checks.is_running("definitely-not-a-real-process-xyz") is False


def test_check_services_structure():
    results = health_checks.check_services(["definitely-not-a-real-process-xyz"])
    assert len(results) == 1
    ok, msg = results[0]
    assert ok is False
    assert "NOT running" in msg


def test_osa_escape_quotes_and_backslashes():
    # Backslash is escaped first, then the double-quote, so the result stays a
    # valid AppleScript string literal.
    assert health_checks.osa_escape('a"b') == 'a\\"b'
    assert health_checks.osa_escape("a\\b") == "a\\\\b"
    assert health_checks.osa_escape('back\\and"quote') == 'back\\\\and\\"quote'


def test_osa_escape_noop_for_plain_text():
    assert health_checks.osa_escape("2 health check(s) FAILED") == "2 health check(s) FAILED"
