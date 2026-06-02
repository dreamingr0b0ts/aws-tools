# Environment Bootstrap

One command to scaffold a new **Python** project with sensible defaults:
directory structure, a virtualenv with dev dependencies, linting config, a git
repo with a pre-commit lint hook, and env files.

The bootstrap script itself uses **only the Python standard library** — no
install step required to run it.

## What it creates

```
<project>/
├── <package>/__init__.py     # package (name sanitized: my-app -> my_app)
├── tests/test_smoke.py       # a trivial passing test
├── pyproject.toml            # project metadata + ruff + pytest config
├── requirements.txt          # runtime deps (empty to start)
├── requirements-dev.txt      # ruff, pytest
├── .gitignore
├── .env.example              # template, committed
├── .env                      # copied from .env.example, git-ignored
├── README.md
├── .venv/                    # virtualenv
└── .git/
    └── hooks/pre-commit      # runs `ruff check .` before every commit
```

## What it does, step by step

1. **Files** — writes the structure above (package name is derived from the
   project name with `-`/spaces converted to `_`, lowercased).
2. **git** — `git init` (skipped if the directory is already a repo).
3. **venv** — creates `.venv` with the Python running the script.
4. **Dependencies** — `pip install -r requirements-dev.txt` into the venv
   (skip with `--skip-install`).
5. **pre-commit hook** — installs an executable `.git/hooks/pre-commit` that
   runs `ruff check .` (preferring the venv's ruff, falling back to a system
   ruff). A failing lint blocks the commit.
6. **.env** — copies `.env.example` to `.env` if one doesn't already exist.

## Requirements

- Python 3.9+ (for the generated project; the script runs on 3.8+)
- `git` on PATH
- Network access for step 4 (or use `--skip-install`)

## Usage

```bash
# Bootstrap into a new directory (package name = directory name)
python3 environment_bootstrap.py ~/code/my-app

# Override the package name
python3 environment_bootstrap.py ~/code/my-app --name myapp

# Scaffold without installing dependencies (offline)
python3 environment_bootstrap.py ~/code/my-app --skip-install

# Allow bootstrapping into a non-empty directory
python3 environment_bootstrap.py ~/code/existing --force
```

### Options

| Flag             | Description                                                  |
|------------------|--------------------------------------------------------------|
| `path`           | Target project directory (positional, required).             |
| `--name PKG`     | Package name (default: the directory name, sanitized).       |
| `--force`        | Allow bootstrapping into a non-empty directory.              |
| `--skip-install` | Create the venv but skip `pip install` of dev dependencies.  |

## After bootstrapping

```bash
cd <project>
source .venv/bin/activate        # Windows: .venv\Scripts\activate
ruff check .                     # lint
pytest                           # run tests
```

The pre-commit hook runs automatically on `git commit`. To bypass it for a
single commit (not recommended): `git commit --no-verify`.

## Notes & caveats

- Re-running on an existing project: file writes **overwrite** the scaffolded
  files (e.g. `pyproject.toml`, `.gitignore`). Use `--force` deliberately and
  expect those files to be reset. `.env` is preserved if it already exists.
- The pre-commit hook is a plain shell script, not the [pre-commit](https://pre-commit.com)
  framework — zero extra dependencies, but also no multi-tool config. Swap in
  the framework later if you outgrow it.
- The hook lints the whole tree (`ruff check .`), not just staged files, for
  simplicity.
- Defaults to a **flat layout** (package at the project root) so `import
  <package>` and `pytest` work without extra path configuration.
