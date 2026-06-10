import tag_compliance


def test_parse_set_basic():
    assert tag_compliance.parse_set(["owner=alice", "environment=prod"]) == {
        "owner": "alice",
        "environment": "prod",
    }


def test_parse_set_empty_and_none():
    assert tag_compliance.parse_set(None) == {}
    assert tag_compliance.parse_set([]) == {}


def test_parse_set_value_with_equals_and_blank():
    # Everything after the first '=' is the value; a bare key gets "".
    assert tag_compliance.parse_set(["url=https://x?a=b", "owner="]) == {
        "url": "https://x?a=b",
        "owner": "",
    }
