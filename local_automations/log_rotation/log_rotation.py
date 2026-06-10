#!/usr/bin/env python3
"""Rotate and clean up log files on a local dev machine.

For each given directory, gzip-compresses logs older than --compress-days and
deletes logs (compressed or not) older than --delete-days. File age is based on
modification time, which is preserved across compression.

DRY-RUN by default; pass --run to actually compress/delete.

    python3 log_rotation.py ~/myapp/logs
    python3 log_rotation.py ~/logs --compress-days 7 --delete-days 30 --run
"""

import argparse
import gzip
import os
import shutil
import time
from pathlib import Path


def find(paths, pattern, recursive):
    seen = set()
    for raw in paths:
        d = Path(raw).expanduser()
        if not d.is_dir():
            print(f"! skip non-directory: {d}")
            continue
        for pat in (pattern, pattern + ".gz"):
            for f in d.rglob(pat) if recursive else d.glob(pat):
                if f.is_file() and f not in seen:
                    seen.add(f)
                    yield f


def compress(f):
    gz = f.with_name(f.name + ".gz")
    st = f.stat()
    with open(f, "rb") as fi, gzip.open(gz, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    os.utime(gz, (st.st_atime, st.st_mtime))  # keep age for future cleanup
    f.unlink()


def main():
    p = argparse.ArgumentParser(description="Rotate/clean up local log files.")
    p.add_argument("paths", nargs="+", help="Log directories to process.")
    p.add_argument("--pattern", default="*.log", help="Log filename glob (default: *.log).")
    p.add_argument(
        "--compress-days",
        type=int,
        default=7,
        help="Gzip logs older than this many days (default: 7).",
    )
    p.add_argument(
        "--delete-days",
        type=int,
        default=30,
        help="Delete logs older than this many days (default: 30).",
    )
    p.add_argument("-r", "--recursive", action="store_true", help="Recurse into subdirectories.")
    p.add_argument("--run", action="store_true", help="Apply changes (default: dry-run).")
    args = p.parse_args()

    now = time.time()
    mode = "RUN" if args.run else "DRY-RUN"
    print(
        f"=== Log rotation [{mode}] | compress >{args.compress_days}d, "
        f"delete >{args.delete_days}d ===\n"
    )

    compressed = deleted = freed = 0
    for f in find(args.paths, args.pattern, args.recursive):
        st = f.stat()
        age = (now - st.st_mtime) / 86400
        if age >= args.delete_days:
            print(f"  delete   {f} ({age:.0f}d)")
            if args.run:
                f.unlink()
            deleted += 1
            freed += st.st_size
        elif age >= args.compress_days and f.suffix != ".gz":
            print(f"  compress {f} ({age:.0f}d)")
            if args.run:
                compress(f)
            compressed += 1

    print(
        f"\ncompressed {compressed}, deleted {deleted}, "
        f"reclaimed ~{freed / 1e6:.1f} MB (deletions only)."
    )


if __name__ == "__main__":
    main()
