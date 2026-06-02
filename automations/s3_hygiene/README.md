# S3 Hygiene

Reports S3 buckets with common hygiene problems:

| Flag           | Meaning                                                            |
|----------------|-------------------------------------------------------------------|
| `PUBLIC`       | Bucket is reachable by anyone (public policy or public ACL grant) and not fully locked down by a Public Access Block. |
| `unencrypted`  | Bucket has no server-side encryption configuration.               |
| `no-lifecycle` | Bucket has no lifecycle policy (no automatic expiration/transition). |

This tool is **read-only** — it never modifies any bucket. It lists every
bucket in the account, resolves each bucket's region, and queries it there to
avoid cross-region redirect errors.

## How "public" is determined

For each bucket the script checks, in order:

1. **Public Access Block** — if all four settings (`BlockPublicAcls`,
   `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`) are on, the
   bucket is treated as **not public** and the other checks are skipped.
2. **Bucket policy status** — `get_bucket_policy_status` → `IsPublic`.
3. **Bucket ACL** — any grant to the `AllUsers` or `AuthenticatedUsers` groups.

If step 2 or 3 indicates public access (and step 1 didn't lock it down), the
bucket is flagged `PUBLIC`.

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions (all read-only)

```
s3:ListAllMyBuckets
s3:GetBucketLocation
s3:GetBucketPublicAccessBlock
s3:GetBucketPolicyStatus
s3:GetBucketAcl
s3:GetEncryptionConfiguration
s3:GetLifecycleConfiguration
```

## Setup

```bash
cd s3_hygiene
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python3 s3_hygiene.py
```

### Example output

```
=== S3 hygiene | 4 bucket(s) ===

my-public-site [us-east-1]: PUBLIC, no-lifecycle
old-logs-bucket [us-west-2]: no-lifecycle
legacy-data [eu-west-1]: unencrypted, no-lifecycle

3 of 4 bucket(s) flagged.
```

## Notes & caveats

- **Default encryption:** since January 2023 S3 applies SSE-S3 encryption to all
  new buckets automatically, so `get_bucket_encryption` usually returns a
  configuration and the `unencrypted` flag rarely fires. It still catches the
  rare bucket whose encryption configuration was explicitly removed.
- The Public Access Block check considers only the **bucket-level** block.
  Account-level Public Access Block settings are not read here; if you enforce
  blocking at the account level, treat the `PUBLIC` flag as "publicly configured"
  rather than necessarily reachable.
- A `no-lifecycle` flag is informational, not a security issue — lifecycle
  policies mainly control cost (expiring old objects, transitioning to cheaper
  storage classes).

## Scheduling

Run a recurring report (e.g. weekly) via cron:

```cron
0 9 * * 1 cd /path/to/s3_hygiene && ./.venv/bin/python s3_hygiene.py
```
