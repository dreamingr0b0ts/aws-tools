# Snapshot & Pruning

Automates point-in-time backups: creates **EBS** and **RDS** snapshots for
resources you've tagged for backup, then prunes (deletes) old snapshots beyond a
retention window. Designed to run on a schedule (cron / EventBridge).

## What it does

For each region:

1. **Select** EBS volumes and RDS instances tagged `--tag-key=--tag-value`
   (default `backup=true`).
2. **Create** a snapshot of each selected resource.
3. **Prune** snapshots **previously created by this tool** that are older than
   `--retention-days`.

## ⚠️ Safety

- **Dry-run is the default.** Without `--run` the tool only prints the snapshots
  it *would* create and prune — nothing changes.
- **Pruning only ever deletes this tool's own snapshots.** It identifies them by:
  - **EBS:** the tag `auto-snapshot=1` applied at creation.
  - **RDS:** the snapshot identifier prefix `auto-`.

  Manual snapshots, AWS Backup snapshots, and anything created by other tooling
  are never deleted.
- Snapshot **deletion is irreversible.** Review a dry-run before scheduling
  `--run`, and make sure `--retention-days` matches your recovery needs.

## How "ours" is tracked

| Service | Created with                                   | Pruned by matching                 |
|---------|------------------------------------------------|------------------------------------|
| EBS     | tag `auto-snapshot=1` + `source-volume=<id>`   | tag `auto-snapshot=1`              |
| RDS     | identifier `auto-<db-id>-<UTC timestamp>`      | identifier prefix `auto-`          |

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions

Read/plan (dry-run):

```
ec2:DescribeRegions
ec2:DescribeVolumes
ec2:DescribeSnapshots
rds:DescribeDBInstances
rds:DescribeDBSnapshots
rds:ListTagsForResource
```

Additional permissions required for `--run`:

```
ec2:CreateSnapshot
ec2:CreateTags
ec2:DeleteSnapshot
rds:CreateDBSnapshot
rds:AddTagsToResource
rds:DeleteDBSnapshot
```

## Setup

```bash
cd snapshot_and_pruning
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Tag your resources

Tag any EBS volume or RDS instance you want backed up:

```bash
aws ec2 create-tags --resources vol-0abc123 --tags Key=backup,Value=true
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:us-east-1:123456789012:db:mydb \
  --tags Key=backup,Value=true
```

## Usage

```bash
# Preview what would happen (safe), all regions, 7-day retention
python3 snapshot_and_pruning.py

# Actually create + prune snapshots
python3 snapshot_and_pruning.py --run

# Keep 30 days, only us-east-1
python3 snapshot_and_pruning.py --run --retention-days 30 --regions us-east-1

# Use a different selection tag
python3 snapshot_and_pruning.py --run --tag-key backup-daily --tag-value yes
```

### Options

| Flag                | Default        | Description                                          |
|---------------------|----------------|------------------------------------------------------|
| `--run`             | off (dry-run)  | Actually create/delete snapshots.                    |
| `--retention-days`  | `7`            | Delete tool-created snapshots older than this.       |
| `--tag-key`         | `backup`       | Selection tag key.                                   |
| `--tag-value`       | `true`         | Selection tag value.                                 |
| `--regions`         | all enabled    | Regions to operate in.                               |

### Example output (dry-run)

```
=== Snapshot scheduler [DRY-RUN] | select backup=true | retention 7d ===

[us-east-1]
  EBS snapshot of vol-0abc123
  RDS snapshot of mydb -> auto-mydb-20260602-180000
  prune EBS snapshot snap-0old111 (2026-05-20)
```

## Scheduling

Run daily with cron (note the `--run` flag):

```cron
0 3 * * * cd /path/to/snapshot_and_pruning && ./.venv/bin/python snapshot_and_pruning.py --run --retention-days 7
```

Or package as a Lambda on an EventBridge schedule, granting the role the
permissions listed above.

## Notes & caveats

- EBS snapshots are incremental, so daily snapshots cost far less than the full
  volume size after the first one.
- RDS `create_db_snapshot` requires the instance to be `available`; instances
  mid-modify/backup are skipped with an error for that region.
- Snapshots are created **asynchronously** — the tool kicks them off and returns;
  it does not wait for completion.
- RDS snapshot identifiers must be unique; the UTC timestamp makes collisions
  unlikely, but running twice within the same second for one instance will fail
  the second call.
- For more advanced policies (cross-region copy, app-consistent backups), also
  consider AWS Backup or Data Lifecycle Manager.
