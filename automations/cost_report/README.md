# Cost Report

Pulls AWS spend **by service** from the Cost Explorer API and posts a formatted
summary to Slack (or prints it). It reports two windows in one run:

- **Daily** — yesterday's spend per service.
- **Month-to-date (MTD)** — first of the current month through today.

Services are ranked highest-cost first, line items under $0.01 are hidden, and a
grand total is shown for each window.

## How it works

1. Calls `ce:GetCostAndUsage` twice (DAILY and MONTHLY granularity), grouped by
   the `SERVICE` dimension, using the `UnblendedCost` metric.
2. Aggregates and sorts the results into a readable summary.
3. If `SLACK_WEBHOOK_URL` is set, POSTs the summary to that Slack incoming
   webhook (via `urllib`, no extra dependency). Otherwise it prints to stdout
   only.

Cost Explorer is a global service, so the client is always created in
`us-east-1` regardless of your default region.

> On the 1st of the month, MTD has no full day of data yet, so the start date
> falls back to yesterday (the last day of the previous month) to keep the call
> valid. On that day the second section is labeled **"Latest full day"** rather
> than "Month-to-date", so the window isn't misreported.

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- Cost Explorer **enabled** in the account (Billing console → Cost Explorer).
- AWS credentials available via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permission

```json
{
  "Effect": "Allow",
  "Action": "ce:GetCostAndUsage",
  "Resource": "*"
}
```

## Setup

```bash
cd cost_report
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Print the report to the terminal
python3 cost_report.py

# Also post it to Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
python3 cost_report.py
```

### Example output

```
*Daily spend (2026-06-01)*
  • Amazon Elastic Compute Cloud - Compute: $12.40
  • Amazon Simple Storage Service: $3.18
  • AWS Lambda: $0.42
*Total: $16.00*

*Month-to-date (2026-06-01 → 2026-06-02)*
  • Amazon Elastic Compute Cloud - Compute: $12.40
  • Amazon Simple Storage Service: $3.18
*Total: $15.58*
```

## Environment variables

| Variable            | Required | Description                                  |
|---------------------|----------|----------------------------------------------|
| `SLACK_WEBHOOK_URL` | No       | Slack incoming webhook; if unset, prints only. |
| `AWS_PROFILE`       | No       | Named profile to use from `~/.aws/credentials`. |
| `AWS_REGION`        | No       | Default region (does not affect Cost Explorer). |

## Scheduling

Run it daily with cron (e.g. 08:00 local):

```cron
0 8 * * * cd /path/to/cost_report && SLACK_WEBHOOK_URL=... ./.venv/bin/python cost_report.py
```

Or package it as an AWS Lambda on an EventBridge schedule (set the webhook as a
Lambda environment variable and give the role the `ce:GetCostAndUsage`
permission).

## Notes & caveats

- Each Cost Explorer API request costs about **$0.01**; this script makes two
  per run.
- `UnblendedCost` shows usage costs and does **not** include refunds, credits,
  or tax unless you adjust the metric/filters.
- Cost Explorer data can lag several hours, so "today" may be incomplete.
