#!/usr/bin/env python3
"""Release helper: bump the version in pyproject.toml, update CHANGELOG.md,
commit, tag, and optionally push.

Local steps (bump, changelog, commit, tag) run by default. Pushing to the remote
requires --push. Use --dry-run to preview without changing anything.

    python3 release_helper.py patch           # 1.2.3 -> 1.2.4 (local only)
    python3 release_helper.py minor --push    # also push commit + tag to origin
    python3 release_helper.py --set 2.0.0
    python3 release_helper.py patch --dry-run
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

VERSION_RE = re.compile(r'(?m)^(version\s*=\s*")(\d+)\.(\d+)\.(\d+)(")')


def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"error: {' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def bump(cur, part):
    a, b, c = cur
    return {"major": (a + 1, 0, 0), "minor": (a, b + 1, 0), "patch": (a, b, c + 1)}[part]


def read_version(pp):
    m = VERSION_RE.search(pp.read_text())
    if not m:
        sys.exit("error: no 'version = \"X.Y.Z\"' found in pyproject.toml")
    return int(m.group(2)), int(m.group(3)), int(m.group(4))


def changelog_section(version):
    last = sh(["git", "describe", "--tags", "--abbrev=0"], check=False)
    rng = f"{last}..HEAD" if last else "HEAD"
    log = sh(["git", "log", rng, "--no-merges", "--pretty=format:- %s"], check=False)
    return f"## v{version} - {date.today()}\n\n{log or '- No changes.'}\n"


def write_changelog(section):
    path = Path("CHANGELOG.md")
    existing = (
        re.sub(r"(?s)^# Changelog\n+", "", path.read_text(), count=1) if path.exists() else ""
    )
    path.write_text(f"# Changelog\n\n{section}\n{existing}".rstrip() + "\n")


def main():
    p = argparse.ArgumentParser(description="Bump version, changelog, tag, push.")
    p.add_argument(
        "part", nargs="?", choices=["major", "minor", "patch"], help="Which semver part to bump."
    )
    p.add_argument("--set", dest="exact", help="Set an explicit version X.Y.Z.")
    p.add_argument("--push", action="store_true", help="Push the commit and tag to origin.")
    p.add_argument("--dry-run", action="store_true", help="Preview without changing anything.")
    p.add_argument("--allow-dirty", action="store_true", help="Skip the clean-working-tree check.")
    args = p.parse_args()

    if not args.part and not args.exact:
        p.error("specify a bump part (major|minor|patch) or --set X.Y.Z")

    pp = Path("pyproject.toml")
    if not pp.exists():
        sys.exit("error: pyproject.toml not found in current directory")
    if not args.allow_dirty and sh(["git", "status", "--porcelain"]):
        sys.exit("error: working tree not clean (commit/stash first, or --allow-dirty)")

    cur = read_version(pp)
    if args.exact:
        if not re.fullmatch(r"\d+\.\d+\.\d+", args.exact):
            sys.exit("error: --set expects X.Y.Z")
        new = args.exact
    else:
        new = ".".join(map(str, bump(cur, args.part)))

    tag = f"v{new}"
    section = changelog_section(new)

    if args.dry_run:
        print(f"[dry-run] {'.'.join(map(str, cur))} -> {new}, tag {tag}\n")
        print(section)
        return

    pp.write_text(VERSION_RE.sub(rf"\g<1>{new}\g<5>", pp.read_text(), count=1))
    write_changelog(section)
    sh(["git", "add", "pyproject.toml", "CHANGELOG.md"])
    sh(["git", "commit", "-m", f"release: {tag}"])
    sh(["git", "tag", "-a", tag, "-m", tag])
    print(f"Committed and tagged {tag}.")

    if args.push:
        branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        sh(["git", "push", "origin", branch])
        sh(["git", "push", "origin", tag])
        print(f"Pushed {branch} and {tag} to origin.")
    else:
        print(f"Not pushed. To publish:\n  git push origin HEAD && git push origin {tag}")


if __name__ == "__main__":
    main()
