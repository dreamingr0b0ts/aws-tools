#!/usr/bin/env python3
"""Pre-commit quality gate: format, lint, and run fast tests on staged Python files.

Run the checks now, or install it as this repo's git pre-commit hook:

    python3 precommit_checks.py --install   # from inside the target repo
    python3 precommit_checks.py             # run the checks manually

Exits non-zero (blocking the commit) if formatting fails, lint finds issues, or
tests fail. Missing tools (ruff / pytest) are skipped with a warning. Tools are
taken from ./.venv if present, otherwise from PATH.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def repo_root():
    r = sh(["git", "rev-parse", "--show-toplevel"])
    if r.returncode != 0:
        sys.exit("error: not inside a git repository")
    return Path(r.stdout.strip())


def staged_py():
    r = sh(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [f for f in r.stdout.splitlines() if f.endswith(".py")]


def tool(name):
    local = Path(".venv") / ("Scripts" if os.name == "nt" else "bin") / name
    return str(local) if local.exists() else shutil.which(name)


def stage(label, cmd):
    print(f"[{label}] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def install():
    hook = repo_root() / ".git" / "hooks" / "pre-commit"
    hook.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).resolve()}"\n')
    hook.chmod(0o755)
    print(f"Installed pre-commit hook -> {hook}")


def main():
    p = argparse.ArgumentParser(description="Format, lint and test staged Python files.")
    p.add_argument("--install", action="store_true",
                   help="Install this script as the repo's git pre-commit hook.")
    args = p.parse_args()
    if args.install:
        install()
        return

    files = staged_py()
    if not files:
        print("No staged Python files; skipping checks.")
        return

    failed = []
    ruff = tool("ruff")
    if ruff:
        if stage("format", [ruff, "format", *files]) != 0:
            failed.append("format")
        else:
            subprocess.run(["git", "add", *files])  # re-stage any reformatting
        if stage("lint", [ruff, "check", *files]) != 0:
            failed.append("lint")
    else:
        print("! ruff not found; skipping format + lint")

    pytest = tool("pytest")
    if pytest:
        if stage("test", [pytest, "-q", "-x"]) not in (0, 5):  # 5 = no tests collected
            failed.append("test")
    else:
        print("! pytest not found; skipping tests")

    if failed:
        sys.exit(f"\npre-commit FAILED: {', '.join(failed)}")
    print("\npre-commit passed.")


if __name__ == "__main__":
    main()
