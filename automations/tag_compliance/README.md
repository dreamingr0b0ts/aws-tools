# Tag Compliance

Scans AWS resources for **missing required tags** (default: `owner`,
`environment`, `cost-center`) and either reports the gaps or auto-fills them.

By default it runs in **report** mode and changes nothing. Pass `--apply` (with
`--set` values) to write the missing tags.

## How it works

1. Uses the **Resource Groups Tagging API** (`get_resources`), which returns
   taggable resources and their current tags across most AWS services in a
   region — one API surface instead of per-service calls.
2. For each resource, computes which required keys are absent.
3. In report mode, prints the resource ARN and its missing keys.
4. In `--apply` mode, calls `tag_resources` to write **only the missing keys**,
   using the default values you supply via `--set`. Existing tags are never
   overwritten.

It scans **all enabled regions** by default (or a subset via `--regions`).
Errors in a single region are caught and skipped so the rest of the scan
continues.

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions

Read-only (report):

```
ec2:DescribeRegions
tag:GetResources
```

Additional permission required only for `--apply`:

```
tag:TagResources
```

> Note: `tag:TagResources` is the Tagging-API action. Under the hood it calls
> each service's own tagging API, so the principal must also be allowed to tag
> the specific resource types in scope (e.g. `ec2:CreateTags`, `s3:PutBucketTagging`,
> etc.). Grant those as needed for the resources you intend to tag.

## Setup

```bash
cd tag_compliance
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Report resources missing the default required tags, all regions
python3 tag_compliance.py

# Use a custom set of required tags
python3 tag_compliance.py --required owner environment cost-center team

# Limit to specific regions
python3 tag_compliance.py --regions us-east-1 us-west-2

# Auto-fill missing tags with default values (writes only the missing keys)
python3 tag_compliance.py --apply --set owner=unassigned environment=prod cost-center=0000
```

### Options

| Flag         | Default                            | Description                                            |
|--------------|------------------------------------|--------------------------------------------------------|
| `--required` | `owner environment cost-center`    | Required tag keys to check for.                        |
| `--apply`    | off (report only)                  | Write missing tags using `--set` values.               |
| `--set`      | —                                  | `KEY=VALUE` defaults for missing tags (required with `--apply`). |
| `--regions`  | all enabled                        | Space-separated list of regions to scan.               |

### Example output (report)

```
=== Tag compliance [REPORT] | required: owner, environment, cost-center ===

[us-east-1]
  arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123
    missing: owner, cost-center
  arn:aws:s3:::my-bucket
    missing: environment
```

## Notes & caveats

- **Tag keys are case-sensitive.** `Owner` and `owner` are different tags;
  list keys exactly as your tagging standard defines them.
- `--apply` only fills keys that are **missing**. It will not change or
  overwrite a resource's existing tag values.
- A resource only appears for a key it lacks; resources fully compliant with the
  required set are silently skipped.
- The Tagging API covers most but not every resource type. Resource types it
  doesn't support won't be returned by the scan.

## Scheduling

Run a recurring **report** (e.g. weekly) via cron and review before applying:

```cron
0 9 * * 1 cd /path/to/tag_compliance && ./.venv/bin/python tag_compliance.py
```
