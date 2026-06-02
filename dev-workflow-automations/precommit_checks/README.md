# Pre-commit Checks

A standalone quality gate that runs **before every commit**: it formats, lints,
and runs fast tests on your **staged Python files**, blocking the commit if
anything fails.

Stdlib-only — it shells out to `ruff` and `pytest` but needs nothing installed
to run itself.

## What it does

On each run (or each `git commit` once installed):

1. Collects staged Python files (`git diff --cached`, added/copied/modified). If
   there are none, it exits immediately and lets the commit through.
2. **format** — `ruff format <staged files>`, then re-stages them so the
   formatting is included in the commit.
3. **lint** — `ruff check <staged files>`; lint errors block the commit.
4. **test** — `pytest -q -x` (stop on first failure). "No tests collected"
   (exit code 5) counts as a pass.

If any stage fails, it exits non-zero and the commit is aborted.

## Tool resolution & graceful skips

- Tools are taken from `./.venv/bin` (or `.venv\Scripts` on Windows) if present,
  otherwise from `PATH`.
- If `ruff` isn't found, format + lint are skipped with a warning. If `pytest`
  isn't found, tests are skipped. The gate never blocks a commit just because a
  tool is missing.

## Requirements

- Python 3.8+
- `git`
- `ruff` and `pytest` for the checks to actually run (e.g.
  `pip install ruff pytest`). Without them the relevant stages are skipped.

## Usage

```bash
# Run the checks against the current staged files
python3 precommit_checks.py

# Install as this repo's git pre-commit hook (run from inside the repo)
python3 precommit_checks.py --install
```

After `--install`, the checks run automatically on `git commit`. The installed
hook pins both the Python interpreter and this script by absolute path, so it
keeps working regardless of the active virtualenv at commit time.

To bypass the hook for one commit (not recommended):

```bash
git commit --no-verify
```

## Example

```
$ git commit -m "add feature"
[format] ruff format app/feature.py
[lint] ruff check app/feature.py
[test] pytest -q -x
.....
pre-commit passed.
```

A failure looks like:

```
[lint] ruff check app/feature.py
app/feature.py:3:1: F401 `os` imported but unused

pre-commit FAILED: lint
```

## Notes & caveats

- **Partial staging:** the format stage runs on the working-tree copy of each
  staged file and then re-stages it. If a file has *both* staged and unstaged
  changes, re-staging will pull the unstaged changes into the commit too. Avoid
  committing partially-staged files through this hook, or stash the rest first.
- The test stage runs the **whole** suite (`pytest -q -x`). For larger projects,
  keep it fast by marking slow tests (`@pytest.mark.slow`) and changing the
  command to `pytest -q -x -m "not slow"`.
- Lint/format only touch **staged** files; tests run for the whole project so a
  change can't silently break an untouched module.
- This is intentionally lightweight. For multi-language hooks or a shared team
  config, consider the [pre-commit](https://pre-commit.com) framework instead.
