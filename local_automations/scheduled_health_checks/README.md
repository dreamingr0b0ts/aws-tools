# Scheduled Health Checks

Lightweight health checks for a local dev machine — **disk usage** and **running
services** — with notifications when something is wrong. Stdlib-only.

## What it checks

- **Disk usage** — for each mount point, alerts when usage is at or above
  `--disk-threshold` (default 90%). Reports percent used and free GB.
- **Services** — for each name, checks whether a process with that name is
  running.

## Notifications

The full report always prints to stdout. **On failures only**, it additionally:

- Posts the report to Slack if `SLACK_WEBHOOK_URL` is set.
- Shows a macOS desktop notification (via `osascript`) when available.
- Exits with status **1** so cron, a launchd agent, or a monitoring wrapper can
  detect the failure. A fully healthy run exits 0.

## How service detection works

It reads `ps -A -o comm=` and compares the **basename** of each process to the
names you provide. This is portable across macOS (where `comm` is a full path
like `/sbin/launchd`) and Linux (where it's the bare command name). Linux
truncates `comm` to 15 characters; the matcher tolerates that case.

> This checks *process presence*, not service-manager state. It does not query
> `systemd`/`launchd`, so a crashed-but-being-restarted unit may flap. For
> authoritative service state, wrap `systemctl is-active <unit>` instead.

## Requirements

- Python 3.8+ (standard library only)
- `ps` (present on macOS and Linux)
- Optional: `SLACK_WEBHOOK_URL` env var for Slack alerts

## Usage

```bash
# Default: check / against 90%, no services
python3 health_checks.py

# Check several mounts and required services
python3 health_checks.py --mounts / /data --disk-threshold 85 \
    --service docker postgres nginx

# Send Slack alerts on failure
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
python3 health_checks.py --service docker
```

### Options

| Flag                | Default | Description                                           |
|---------------------|---------|-------------------------------------------------------|
| `--mounts`          | `/`     | Mount points to check.                                |
| `--disk-threshold`  | `90`    | Alert when usage % is at or above this.               |
| `--service`         | none    | Process names that must be running.                   |

### Example output

```
=== Health check ===
OK   disk /: 25% used (368.5 GB free)
FAIL disk /data: 94% used (12.0 GB free)
OK   service docker: running
FAIL service postgres: NOT running
```

(exit code 1; Slack + desktop alert sent)

## Scheduling

cron (every 15 minutes), with Slack alerts:

```cron
*/15 * * * * SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
  /usr/bin/python3 /path/to/health_checks.py --service docker postgres
```

On macOS you can also run it from a launchd agent on an interval if you prefer
desktop notifications over cron email.

## Notes & caveats

- Process matching is by **name**, so it can't distinguish two different
  programs that share an executable name.
- Disk usage uses `shutil.disk_usage`, which reports on the filesystem
  containing the given path — pass an actual mount point for per-volume numbers.
- The Slack call has a 10s timeout and failures are non-fatal (printed, not
  raised) so a notification outage won't mask the health result.
