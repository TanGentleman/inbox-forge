# inbox-forge roadmap

inbox-forge turns a folder of exported `.eml` files into one JSON file per email, saves
attachments, and builds a local full-text index you can search by sender, recipient,
subject, content and date. It is offline: no mail account, IMAP or API. For anyone with a
pile of exported mail (Gmail Takeout, Apple Mail, Thunderbird) who wants it searchable.

## Status (upstream main ffdfe27, checked 2026-11-08)

- Last commit 2025-01-18. Runs on Python 3.12, 3.13 and 3.14 with whoosh 2.7.4:
  `python -m src.cli.ingest <dir>` then `python -m src.cli.search <query>` work on the
  fixtures in `tests/fixtures/`. No tests, CI or lockfile upstream.
- Bugs found by running it (fixed on `-1`, each with a test):
  - `ingest -d DIR` always fails: it needs `DIR/search_index` to exist, then cannot open
    the empty index. The ID list and summary ignored `-d` anyway. `search -d` rejected every
    path except the default.
  - `--include-html` crashes on any plain-text-only email (`str + None`).
  - An email that fails during ingest is written to `email_ids.txt` and skipped as a
    duplicate on every later run (reproduced with `--include-html`).
  - `To: "Doe, John" <john@x>` was split on the comma into two recipients.
  - `USAGE.md` documents `python -m src.main`, `src.scripts.*`, `--output` and
    `--exclude-html`; none exist.
- Still broken or stale:
  - whoosh 2.7.4 (2016) is unmaintained; it prints SyntaxWarnings on 3.12+ and its homepage
    (bitbucket.org/mchaput/whoosh) is a 404. The fork whoosh-reloaded last released 2024-02.
  - The package is named `src` and the default data dir is `<checkout>/data`, so it can't be
    pip-installed usefully.
  - HTML-only emails index as `[Could not extract email body]` unless `--include-html`.
  - `src/server/` is three empty files; `pyproject.toml` is Poetry with no lockfile.
- No credentials, tokens or OAuth files anywhere in upstream history (`git log --all`).
- Open issue #1 (goals list, includes a UI); #2 (path bug) is closed.

## Signal vs noise

Keep: the pipeline `.eml` -> `EmailParser` -> `JsonOrganizer` (JSON + attachments + ID
list) -> `SearchEngine`, and the two CLIs with `from:/to:/subject:` and date filters.

Cut: empty `src/server/`, `config/settings.py` and module-level path constants (one data
dir argument instead), `USAGE.md` (fold into README), TypedDict and docstring bulk,
log-heavy error handling that swallows failures.

## Stack

- `inbox-forge-1`: import, the five fixes above, offline pytest suite on fixture emails, this file.
- `inbox-forge-2`: installable package `inbox_forge` with an `inbox-forge` CLI, data dir
  defaults to `./data`, PEP 621 + uv.lock, ruff, GitHub Actions on 3.10-3.14.
- `inbox-forge-3`: cut dead code and USAGE.md; README rewrite.
- `inbox-forge-4`: replace whoosh with SQLite FTS5 from the standard library (no runtime
  dependencies; a new index fills itself from `processed/`); HTML-only emails indexed as text;
  bodies decoded with their declared charset.
- `inbox-forge-5`: pin ruff 0.17.4, pytest 9.2.0 and hatchling 1.33.0; CI pins checkout v7.0.1 and
  setup-uv v10.3.3 by SHA, uv 0.13.7 and ubuntu-24.04, and runs the README searches. Subprocess
  tests for CLI exit codes and the quick start. README quick start runs through `uv run` (a bare
  `inbox-forge` is not on PATH in a clone), plus query and exit-code tables.
- `inbox-forge-6`: `search` exits 2 (bad usage) instead of 0 after printing the error for an invalid
  `--after`/`--before` date or `--in` field; subprocess tests for both.

`inbox-forge-x-mbox` is a side branch (mbox input) that you may drop; it is not part of this stack.

## Apply upstream

```bash
# in kranti-sandbox
git fetch origin
base=$(git log -1 --format=%H --grep='^Import inbox-forge upstream' origin/inbox-forge-1)
git format-patch --relative=inbox-forge "$base"..origin/inbox-forge-6 -o /tmp/inbox-forge
# in a clean upstream clone at ffdfe27
git am /tmp/inbox-forge/*.patch
uv sync --locked && uv run pytest && uv run ruff check && uv run ruff format --check
```

For one branch, use `origin/inbox-forge-(N-1)..origin/inbox-forge-N`. `-1` alone still uses
Whoosh: test it with `pip install whoosh==2.7.4 pytest && python -m pytest`.

## Needs Tan

- `-4` drops Whoosh for SQLite FTS5. An upstream data dir is upgraded in place (index rebuilt from
  `processed/`); old Whoosh files are left in `search_index/`. Python builds without FTS5 (rare)
  fail with a SearchError.
- `-2` renames the package to `inbox_forge`: `python -m src.cli.*` becomes
  `inbox-forge ingest|search`, and the default data dir is `./data` in the current
  directory instead of `<checkout>/data`.
- `search --dir` now means the data dir (same as `ingest -d`), not the index dir. It only
  ever accepted `data/search_index`, so no working command changes meaning except that one.
- `-6` makes `search` exit 2 for an invalid date or `--in` field (it exited 0). The error text and
  stream (stdout) are unchanged; scripts that relied on exit 0 there will see 2.
- Not verified: `pip install git+https://github.com/TanGentleman/inbox-forge` (works only once
  `-2` is upstream; checked with a locally built wheel), CI on GitHub (its commands were run
  locally), and any real mail export (only fixture and synthetic emails).
