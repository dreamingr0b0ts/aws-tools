import cost_report


def _period(groups):
    return {
        "Groups": [
            {"Keys": [svc], "Metrics": {"UnblendedCost": {"Amount": str(amt)}}}
            for svc, amt in groups
        ]
    }


def test_summarize_aggregates_and_sorts_desc():
    results = [
        _period([("EC2", 1.0), ("S3", 3.0)]),
        _period([("EC2", 4.0), ("S3", 0.5)]),
    ]
    assert cost_report.summarize(results) == [("EC2", 5.0), ("S3", 3.5)]


def test_summarize_empty():
    assert cost_report.summarize([]) == []


def test_format_report_hides_sub_cent_and_totals():
    totals = [("EC2", 5.0), ("Tax", 0.004)]  # Tax rounds below the 0.01 cutoff
    report = cost_report.format_report("Daily", totals)
    assert "*Daily*" in report
    assert "EC2: $5.00" in report
    assert "Tax" not in report  # filtered out (< 0.01)
    assert "Total: $5.00" in report  # total still includes everything


def test_post_to_slack_no_url(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert cost_report.post_to_slack("hi") is False


def test_post_to_slack_swallows_errors(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/hook")

    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(cost_report.urllib.request, "urlopen", boom)
    # A failing webhook must not raise; it returns False instead.
    assert cost_report.post_to_slack("hi") is False
