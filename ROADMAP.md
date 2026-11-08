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

- `inbox-forge-1` (done): import, the five fixes above, offline pytest suite on fixture emails, this file.
- `inbox-forge-2` (done): installable package `inbox_forge` with an `inbox-forge` CLI, data dir
  defaults to `./data`, PEP 621 + uv.lock, ruff, GitHub Actions on 3.10-3.14.
- `inbox-forge-3` (done): cut dead code and USAGE.md; README a stranger gets in 30 seconds.
- `inbox-forge-4` (done): replace whoosh with SQLite FTS5 from the standard library (no
  runtime dependencies; a new index fills itself from `processed/`); HTML-only emails
  indexed as text; bodies decoded with their declared charset.

## Apply a branch upstream

```bash
# in kranti-sandbox: everything after the import commit
base=$(git log -1 --format=%H --grep='^Import inbox-forge upstream' origin/inbox-forge-1)
git format-patch --relative=inbox-forge "$base"..origin/inbox-forge-1 -o /tmp/inbox-forge-1
# in a clean upstream clone at ffdfe27
git clone https://github.com/TanGentleman/inbox-forge && cd inbox-forge
git am /tmp/inbox-forge-1/*.patch
python -m venv .venv && .venv/bin/pip install whoosh==2.7.4 pytest
.venv/bin/python -m pytest -q
```

For a stacked branch, use the previous branch as the base: `origin/inbox-forge-1..origin/inbox-forge-2`,
and apply the stack in order. From `-2` on, test with `uv sync --locked && uv run pytest -q`.
If `git am` rejects a hunk over line endings, retry with `git am --keep-cr`.

## Stack verification (2026-11-08)

Each branch was applied with `git format-patch` + `git am` (in stack order) to a fresh clone
at ffdfe27; the tree matched the branch and the tests passed: 11 on `-1` (pip + whoosh),
11 on `-2` and `-3`, 43 on `-4` (`uv sync --locked && uv run pytest`), plus ruff and the
README commands. `-2` and `-4` also pass on Python 3.10-3.14 (SQLite 3.37 and 3.53);
`-2` was installed from a built wheel.

## Needs Tan

- `-4` drops Whoosh for SQLite FTS5. The 26 search tests from `-3` were written against Whoosh
  first and pass on both; `-4` adds two FTS5-only ones (28 in `test_search.py`). An upstream data dir was upgraded in place (index rebuilt from
  `processed/`); old Whoosh files are left in `search_index/`. Python builds without FTS5
  (rare) would fail with a SearchError.
- `-2` renames the package to `inbox_forge`: `python -m src.cli.*` becomes
  `inbox-forge ingest|search`, and the default data dir is `./data` in the current
  directory instead of `<checkout>/data`.
- The README's `pip install git+https://github.com/TanGentleman/inbox-forge` only works once
  `-2` is upstream; it was checked by installing a locally built wheel.
- CI (`.github/workflows/ci.yml`) passed actionlint and its steps were run locally; it has
  not run on GitHub.
- `search --dir` now means the data dir (same as `ingest -d`), not the index dir. It only
  ever accepted `data/search_index`, so no working command changes meaning except that one.
- Nothing was tested against a real mail export; only the fixture emails here.
