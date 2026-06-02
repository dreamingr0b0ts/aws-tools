# Resource Cleanup

Finds — and optionally deletes — unused or idle AWS resources that quietly cost
money. By default it runs in **dry-run** mode and only reports what it finds;
nothing is deleted unless you pass `--delete`.

## What it detects

| Resource              | Flagged when…                                            |
|-----------------------|----------------------------------------------------------|
| Unattached EBS volume | Volume status is `available` (not attached to any EC2).  |
| Old snapshot          | Owned by you and older than `--days` (default 90).       |
| Unused Elastic IP     | Allocated but has no `AssociationId`.                    |
| Idle load balancer    | Classic ELB with no instances, or ALB/NLB whose target groups have **zero** registered targets. |

It scans **all enabled regions** by default (or a subset via `--regions`).
Errors in a single region (e.g. one that's disabled) are caught and skipped so
the rest of the scan continues.

## ⚠️ Safety

- **Dry-run is the default.** You must pass `--delete` to remove anything.
- **Deletion is irreversible.** Deleted volumes, snapshots, released EIPs, and
  deleted load balancers cannot be recovered.
- The "idle" heuristic is intentionally simple. A brand-new or intentionally
  empty load balancer, or a snapshot you're keeping for compliance, will also be
  flagged. **Always review the dry-run output before running with `--delete`.**

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions

Read-only (dry-run):

```
ec2:DescribeRegions
ec2:DescribeVolumes
ec2:DescribeSnapshots
ec2:DescribeAddresses
elasticloadbalancing:DescribeLoadBalancers
elasticloadbalancing:DescribeTargetGroups
elasticloadbalancing:DescribeTargetHealth
```

Additional permissions required only for `--delete`:

```
ec2:DeleteVolume
ec2:DeleteSnapshot
ec2:ReleaseAddress
elasticloadbalancing:DeleteLoadBalancer
```

## Setup

```bash
cd resource_cleanup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Safe: report only, all regions, snapshots older than 90 days
python3 resource_cleanup.py

# Limit to specific regions
python3 resource_cleanup.py --regions us-east-1 us-west-2

# Change snapshot age threshold to 30 days
python3 resource_cleanup.py --days 30

# Actually delete everything flagged (irreversible)
python3 resource_cleanup.py --delete
```

### Options

| Flag        | Default        | Description                                       |
|-------------|----------------|---------------------------------------------------|
| `--delete`  | off (dry-run)  | Actually delete/release flagged resources.        |
| `--days N`  | `90`           | Snapshot age threshold in days.                   |
| `--regions` | all enabled    | Space-separated list of regions to scan.          |

### Example output (dry-run)

```
=== Resource cleanup [DRY-RUN] | snapshot age > 90d ===

[us-east-1]
  unattached volume vol-0abc123 (100GiB gp3)
  old snapshot snap-0def456 (2025-01-15 100GiB)
  unused EIP 52.1.2.3 (eipalloc-0aaa111)
  idle load balancer my-old-alb (v2)
```

## Recommended workflow

1. Run without flags and review the report.
2. Investigate anything you're unsure about (especially load balancers and
   snapshots).
3. Re-run with `--delete` once you've confirmed the list is safe to remove.

## Scheduling

Run a recurring **dry-run** report (e.g. weekly) via cron and review it before
ever deleting:

```cron
0 9 * * 1 cd /path/to/resource_cleanup && ./.venv/bin/python resource_cleanup.py
```

Avoid scheduling `--delete` unattended unless you fully trust the heuristics for
your environment.
