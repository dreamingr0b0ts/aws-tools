# Release Helper

Automates a release in one command: bumps the version in `pyproject.toml`,
generates a `CHANGELOG.md` entry from git history, commits, tags, and
(optionally) pushes.

## What it does

1. **Bump** the version in `pyproject.toml` — `major`, `minor`, or `patch`
   (semver), or set an explicit version with `--set X.Y.Z`.
2. **Changelog** — collects commit subjects since the last tag (`git describe`
   → `git log <last-tag>..HEAD`) and prepends a dated `## vX.Y.Z` section to
   `CHANGELOG.md` (creating the file if needed).
3. **Commit** the version + changelog changes as `release: vX.Y.Z`.
4. **Tag** an annotated tag `vX.Y.Z`.
5. **Push** the commit and tag to `origin` — only when `--push` is given.

## Safety model

- **Local by default.** Steps 1–4 are local and reversible. Pushing to the
  remote happens **only** with `--push`; otherwise the tool prints the exact
  `git push` commands for you to run.
- **Clean tree required.** It refuses to run if the working tree has
  uncommitted changes, unless you pass `--allow-dirty`.
- **Preview anytime** with `--dry-run` — computes the new version and changelog
  and prints them without writing, committing, or tagging.

## Requirements

- Python 3.8+ (standard library only)
- `git`
- A `pyproject.toml` in the current directory containing a line like
  `version = "1.2.3"` (as produced by the `environment_bootstrap` tool).

## Usage

```bash
# From the repo root, on a clean working tree:

python3 release_helper.py patch          # 1.2.3 -> 1.2.4 (local)
python3 release_helper.py minor          # 1.2.3 -> 1.3.0 (local)
python3 release_helper.py major          # 1.2.3 -> 2.0.0 (local)
python3 release_helper.py --set 2.5.0    # explicit version

python3 release_helper.py patch --push     # local steps + push commit & tag
python3 release_helper.py patch --dry-run  # preview only
```

### Options

| Flag            | Description                                                     |
|-----------------|-----------------------------------------------------------------|
| `part`          | `major`, `minor`, or `patch` (positional).                      |
| `--set X.Y.Z`   | Set an explicit version instead of bumping.                     |
| `--push`        | Push the commit and the new tag to `origin`.                    |
| `--dry-run`     | Show the new version and changelog without changing anything.   |
| `--allow-dirty` | Skip the clean-working-tree check.                              |

(Provide either `part` or `--set`, not neither.)

### Example (dry-run)

```
$ python3 release_helper.py minor --dry-run
[dry-run] 1.2.3 -> 1.3.0, tag v1.3.0

## v1.3.0 - 2026-06-02

- fix logout bug
- add login feature
```

## Notes & caveats

- **Single source of truth:** only `pyproject.toml`'s `version` is updated. If
  you also keep `__version__` in your package, sync it separately or import the
  version from package metadata.
- **First release:** with no existing tags, the changelog includes the entire
  commit history (everything is "since the beginning").
- **Changelog is raw commit subjects.** For nicer notes, write good commit
  messages or adopt Conventional Commits and post-process.
- **`--push` respects your current branch.** It pushes `HEAD` to `origin` and
  the new tag. Be deliberate about running it on a release branch vs. `main`.
- The release commit itself appears in the *next* release's changelog range
  boundary (it's the tagged commit), so it won't clutter future changelogs.
