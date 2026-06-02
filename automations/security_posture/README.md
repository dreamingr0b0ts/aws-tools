# Security Posture

A read-only audit of a few high-value AWS security signals:

| Check                         | What it flags                                                         |
|-------------------------------|-----------------------------------------------------------------------|
| Root account MFA              | Whether the account root user has an MFA device enabled.              |
| IAM users without MFA         | IAM users that have no MFA device registered.                        |
| Old access keys               | **Active** access keys older than `--days` (default 90).             |
| Open security groups          | Security groups with inbound rules allowing `0.0.0.0/0` or `::/0`.   |

The tool **never modifies anything**. IAM checks run once (IAM is global);
the security-group scan runs across all enabled regions.

## How it works

- **Root MFA:** reads `iam:GetAccountSummary` → `AccountMFAEnabled`.
- **IAM users / MFA:** paginates `list_users`, then `list_mfa_devices` per user;
  a user with zero devices is flagged.
- **Access key age:** `list_access_keys` per user; only **Active** keys whose
  `CreateDate` is older than the threshold are reported, with their age in days.
- **Security groups:** `describe_security_groups` per region; any ingress rule
  open to `0.0.0.0/0` (IPv4) or `::/0` (IPv6) is flagged, listing the
  protocol/port range (`ALL` for protocol `-1`).

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions (all read-only)

```
iam:GetAccountSummary
iam:ListUsers
iam:ListMFADevices
iam:ListAccessKeys
ec2:DescribeRegions
ec2:DescribeSecurityGroups
```

## Setup

```bash
cd security_posture
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Full audit, all regions, 90-day key threshold
python3 security_posture.py

# Stricter key-age threshold
python3 security_posture.py --days 30

# Limit the security-group scan to specific regions
python3 security_posture.py --regions us-east-1 us-west-2
```

### Options

| Flag        | Default     | Description                                          |
|-------------|-------------|------------------------------------------------------|
| `--days N`  | `90`        | Active access key age threshold in days.             |
| `--regions` | all enabled | Regions for the security-group scan.                 |

### Example output

```
=== Security posture ===

-- Root account MFA: NOT ENABLED --

-- IAM users without MFA (2) --
  build-bot
  intern-temp

-- Active access keys older than 90d (1) --
  build-bot: AKIAEXAMPLE123 (412d)

-- Security groups open to the world (0.0.0.0/0 or ::/0) --
  [us-east-1] sg-0abc123 (web-sg): tcp/22, tcp/443
  [us-west-2] sg-0def456 (legacy): ALL
```

## Notes & caveats

- An open security group isn't automatically wrong — `tcp/443` to the world is
  normal for a public web server. Pay closest attention to admin ports exposed
  to `0.0.0.0/0` (e.g. SSH `tcp/22`, RDP `tcp/3389`, databases like `tcp/3306`).
- "User without MFA" includes users that may only have programmatic access (no
  console password). MFA matters most for users with console sign-in; review
  the list with that context.
- Only **active** access keys are reported for age. Inactive keys are ignored —
  though unused inactive keys are still worth deleting.
- This is a lightweight check, not a replacement for AWS IAM Access Analyzer,
  Security Hub, or a full CIS benchmark.

## Scheduling

Run a recurring audit (e.g. weekly) via cron:

```cron
0 9 * * 1 cd /path/to/security_posture && ./.venv/bin/python security_posture.py
```
