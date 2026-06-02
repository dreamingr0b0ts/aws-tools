#!/usr/bin/env python3
"""Local health checks (disk usage + running services) with notifications.

Always prints a report to stdout. On failures it also posts to Slack (if
SLACK_WEBHOOK_URL is set) and shows a macOS desktop notification when available,
and exits non-zero (handy for cron/monitoring).

    python3 health_checks.py --mounts / /data --disk-threshold 90 \\
        --service docker postgres
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request


def check_disk(mounts, threshold):
    results = []
    for m in mounts:
        try:
            u = shutil.disk_usage(m)
        except OSError:
            results.append((False, f"disk {m}: path not found"))
            continue
        pct = u.used / u.total * 100
        results.append((pct < threshold,
                        f"disk {m}: {pct:.0f}% used ({u.free / 1e9:.1f} GB free)"))
    return results


def is_running(name):
    # Portable across macOS (comm is a full path) and Linux (bare name, which
    # the kernel truncates to 15 chars -- tolerated below).
    out = subprocess.run(["ps", "-A", "-o", "comm="],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        comm = os.path.basename(line.strip())
        if comm == name or (len(comm) == 15 and name.startswith(comm)):
            return True
    return False


def check_services(names):
    out = []
    for n in names:
        ok = is_running(n)
        out.append((ok, f"service {n}: {'running' if ok else 'NOT running'}"))
    return out


def notify_remote(title, body):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        try:
            req = urllib.request.Request(
                url, data=json.dumps({"text": f"*{title}*\n```{body}```"}).encode(),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"! Slack notify failed: {e}")
    if sys.platform == "darwin" and shutil.which("osascript"):
        subprocess.run(["osascript", "-e",
                        f'display notification "{title}" with title "Health check"'])


def main():
    p = argparse.ArgumentParser(description="Local disk/service health checks.")
    p.add_argument("--mounts", nargs="*", default=["/"],
                   help="Mount points to check (default: /).")
    p.add_argument("--disk-threshold", type=int, default=90,
                   help="Alert when disk usage %% is at or above this (default: 90).")
    p.add_argument("--service", nargs="*", default=[], dest="services",
                   help="Process names that must be running.")
    args = p.parse_args()

    results = check_disk(args.mounts, args.disk_threshold) + check_services(args.services)
    report = "\n".join(("OK   " if ok else "FAIL ") + msg for ok, msg in results)
    print("=== Health check ===")
    print(report)

    failures = sum(1 for ok, _ in results if not ok)
    if failures:
        notify_remote(f"{failures} health check(s) FAILED", report)
        sys.exit(1)


if __name__ == "__main__":
    main()
