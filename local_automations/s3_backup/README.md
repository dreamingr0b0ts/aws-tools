# S3 Backup

Backs up important local folders to an S3 bucket with **versioning enabled**, so
every change keeps a recoverable history of prior file versions. Only changed
files are uploaded on each run.

## How it works

1. **Bucket + versioning** — ensures the target bucket exists (optionally
   creating it with `--create-bucket`) and turns on **S3 versioning**
   (idempotent). With versioning on, re-uploading a changed file keeps the old
   copy as a previous version rather than overwriting it.
2. **Walk** each given folder (recursively) or file.
3. **Change detection** — computes each file's md5 and compares it to an `md5`
   value stored in the S3 object's metadata. Unchanged files are skipped. This
   metadata approach is reliable even for large files, where S3's multipart
   ETag is not a plain md5. A missing object (404) counts as "changed" and is
   uploaded; other errors (e.g. `AccessDenied`, throttling) are raised rather
   than silently treated as a re-upload, so genuine problems surface.
4. **Upload** changed/new files, storing the md5 in metadata for next time.

Object keys preserve the source folder name and structure, e.g. backing up
`~/Documents` with `--prefix laptop` produces keys like
`laptop/Documents/notes/todo.txt`.

## Requirements

- Python 3.8+
- `boto3` (see `requirements.txt`)
- AWS credentials via the standard boto3 chain (env vars,
  `~/.aws/credentials`, or an attached IAM role).

### IAM permissions

```
s3:HeadBucket
s3:PutBucketVersioning
s3:HeadObject
s3:PutObject
s3:CreateBucket        # only with --create-bucket
```

## Setup

```bash
cd s3_backup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Preview which files would be uploaded (offline — no AWS calls)
python3 s3_backup.py my-bucket ~/Documents --dry-run

# Back up one or more folders under a prefix
python3 s3_backup.py my-bucket ~/Documents ~/projects --prefix laptop

# Create the bucket (with versioning) in a specific region, then back up
python3 s3_backup.py my-bucket ~/Documents --create-bucket --region us-west-2
```

### Options

| Flag              | Default                | Description                                       |
|-------------------|------------------------|---------------------------------------------------|
| `bucket`          | —                      | Target S3 bucket (positional).                    |
| `paths`           | —                      | One or more folders/files to back up (positional).|
| `--prefix`        | none                   | Key prefix within the bucket.                     |
| `--region`        | `$AWS_REGION` or `us-east-1` | Region (used for client + bucket creation). |
| `--create-bucket` | off                    | Create the bucket if it doesn't exist.            |
| `--dry-run`       | off                    | List candidate files locally; contacts no AWS.    |

## Restoring

Versions are kept in the bucket. To restore:

```bash
# Latest version of a file
aws s3 cp s3://my-bucket/laptop/Documents/notes.txt ./notes.txt

# List all versions, then download a specific one
aws s3api list-object-versions --bucket my-bucket --prefix laptop/Documents/notes.txt
aws s3api get-object --bucket my-bucket --key laptop/Documents/notes.txt \
  --version-id <VersionId> notes.txt
```

## Security & cost notes

- **Secrets:** backing up a folder uploads *everything* in it, including files
  like `.env` or key material. Review what you point it at. Enable **default
  bucket encryption** (SSE-S3 or SSE-KMS) and keep the bucket private (it is by
  default — do not add public access).
- **Versioning cost:** every changed version is stored and billed. Add a
  lifecycle rule to expire old/noncurrent versions after N days to control cost
  (see the companion `s3_hygiene` tool to spot buckets lacking lifecycle rules).
- **Deletes are not propagated:** this is an additive backup — files deleted
  locally remain in the bucket. That's intentional for backup safety.
- `--dry-run` lists *all* candidate files; it does not check remote state, so it
  can't show which would be skipped as unchanged.

## Scheduling

Run daily via cron:

```cron
0 2 * * * cd /path/to/s3_backup && ./.venv/bin/python s3_backup.py my-bucket ~/Documents --prefix $(hostname)
```
