# Log Rotation

Keeps log directories on a local dev machine tidy: gzip-compresses older logs to
save space and deletes very old ones. Stdlib-only — nothing to install.

## How it works

For each directory you pass, it finds files matching `--pattern` (default
`*.log`) and the rotated form (`*.log.gz`), then for each file, based on its
**modification time**:

- **age ≥ `--delete-days`** (default 30) → delete it (whether `.log` or `.gz`).
- **age ≥ `--compress-days`** (default 7) and not already `.gz` → gzip it to
  `<name>.gz` and remove the original.
- otherwise → leave it alone.

Compression **preserves the original mtime** on the `.gz` file, so age-based
decisions stay correct across runs (a compressed log still ages toward
deletion).

## ⚠️ Safety

- **Dry-run is the default.** Without `--run`, it only prints what it *would*
  compress or delete.
- **Deletion is permanent.** Review the dry-run output and confirm your
  `--delete-days` threshold before using `--run`.

## Usage

```bash
# Preview (safe) — default thresholds, one directory
python3 log_rotation.py ~/myapp/logs

# Apply with custom thresholds
python3 log_rotation.py ~/myapp/logs --compress-days 7 --delete-days 30 --run

# Multiple directories, recurse into subfolders
python3 log_rotation.py ~/app/logs /tmp/logs -r --run

# Different filename pattern
python3 log_rotation.py ~/logs --pattern '*.out' --run
```

### Options

| Flag                | Default | Description                                        |
|---------------------|---------|----------------------------------------------------|
| `paths`             | —       | One or more log directories (positional).          |
| `--pattern`         | `*.log` | Glob for log filenames.                            |
| `--compress-days N` | `7`     | Gzip logs older than N days.                        |
| `--delete-days N`   | `30`    | Delete logs older than N days.                      |
| `-r`, `--recursive` | off     | Recurse into subdirectories.                        |
| `--run`             | off     | Apply changes (otherwise dry-run).                  |

### Example output

```
=== Log rotation [DRY-RUN] | compress >7d, delete >30d ===

  delete   /home/me/app/logs/old.log (45d)
  compress /home/me/app/logs/week.log (10d)

compressed 1, deleted 2, reclaimed ~12.4 MB (deletions only).
```

## Notes & caveats

- `--delete-days` should be **greater than** `--compress-days`; deletion is
  checked first, so a file past the delete threshold is removed rather than
  compressed.
- The reclaimed-space figure counts **deletions only**; compression also saves
  space but isn't included in that number.
- Re-compressing reuses the `<name>.gz` filename. If an active process is still
  writing to a `.log` file, compressing it mid-write isn't safe — point this at
  rotated/inactive logs, not files being actively appended to.
- For system-managed logs (e.g. `/var/log`), prefer the OS's `logrotate`/
  `newsyslog`. This tool is aimed at app and dev logs you own.

## Scheduling

Run daily via cron:

```cron
30 1 * * * /usr/bin/python3 /path/to/log_rotation.py ~/myapp/logs --run
```
