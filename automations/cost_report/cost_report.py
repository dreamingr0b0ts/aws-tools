#!/usr/bin/env python3
"""Report AWS spend by service (Cost Explorer) and post a summary to Slack.

Posts to the Slack incoming webhook in SLACK_WEBHOOK_URL if set, otherwise
prints to stdout only. Cost Explorer is global; its endpoint lives in us-east-1.
"""
import json
import os
import urllib.request
from datetime import date, timedelta

import boto3


def get_costs(granularity, start, end):
    ce = boto3.client("ce", region_name="us-east-1")
    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity=granularity,
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )
    return resp["ResultsByTime"]


def summarize(results):
    totals = {}
    for period in results:
        for group in period["Groups"]:
            svc = group["Keys"][0]
            amt = float(group["Metrics"]["UnblendedCost"]["Amount"])
            totals[svc] = totals.get(svc, 0.0) + amt
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def format_report(title, totals):
    lines = [f"*{title}*"]
    for svc, amt in totals:
        if amt >= 0.01:
            lines.append(f"  \u2022 {svc}: ${amt:,.2f}")
    lines.append(f"*Total: ${sum(a for _, a in totals):,.2f}*")
    return "\n".join(lines)


def post_to_slack(text):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return False
    req = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
    return True


def main():
    today = date.today()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)
    # On the 1st of the month MTD has no full day yet; fall back to yesterday.
    if month_start >= today:
        month_start = yesterday

    daily = summarize(get_costs("DAILY", yesterday.isoformat(), today.isoformat()))
    monthly = summarize(get_costs("MONTHLY", month_start.isoformat(), today.isoformat()))

    report = "\n\n".join([
        format_report(f"Daily spend ({yesterday})", daily),
        format_report(f"Month-to-date ({month_start} \u2192 {today})", monthly),
    ])
    print(report)
    print("\n[posted to Slack]" if post_to_slack(report)
          else "\n[SLACK_WEBHOOK_URL not set; printed only]")


if __name__ == "__main__":
    main()
