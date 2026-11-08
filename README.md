# inbox-forge

Makes a folder of exported `.eml` files (Gmail Takeout, Apple Mail, Thunderbird) searchable on
your machine. `ingest` writes one JSON file per email, saves attachments, and builds a SQLite FTS5
index; `search` queries it. No mail account, IMAP, API keys or network access.

## Quick start

Needs Python 3.10+ built with SQLite FTS5 (python.org, uv and most Linux builds are) and
[uv](https://docs.astral.sh/uv/) (CI uses uv 0.13.7). No runtime dependencies.

```bash
git clone https://github.com/TanGentleman/inbox-forge && cd inbox-forge
uv sync --locked
uv run inbox-forge ingest tests/fixtures              # the two sample emails, into ./data
uv run inbox-forge search quarterly
uv run inbox-forge search "from:alice" --after 2024-01-01
```

```
Found 1 matching emails:

Date: 2024-03-05 10:00
From: Alice Smith <alice@example.com>
To: "Doe, John" <john@example.com> bob@example.com Carol <carol@example.com>
Subject: Quarterly report
ID: 521daea0b43852fd
```

To install the command outside a checkout: `pip install git+https://github.com/TanGentleman/inbox-forge`.

## Commands

```
inbox-forge ingest FOLDER [--data-dir DIR] [--include-html]
inbox-forge search QUERY [--in FIELDS] [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--data-dir DIR]
```

`ingest` reads every `*.eml` under `FOLDER` recursively. Emails it has already stored are skipped,
so you can re-run it on a growing folder; an email that failed is retried next time.
`--include-html` also indexes the HTML part (HTML-only emails are indexed as text either way).

`search` matches subject, body, sender and recipients:

| Query | Matches |
| --- | --- |
| `lunch friday` | both words, any field |
| `from:alice`, `to:bob`, `subject:report` | one field (prefix must start the query) |
| `--in subject,content,sender,recipient` | the listed fields |
| `AND`, `OR`, `NOT`, `"exact phrase"`, `meet*` | FTS5 query syntax; a malformed query falls back to plain words |

| Exit code | When |
| --- | --- |
| 0 | done, including "No matching emails found." and an invalid date or `--in` field (an error is printed) |
| 1 | `ingest` folder does not exist, or ingest failed |
| 2 | bad usage (no command, unknown command, missing argument) |

## Data directory

Both commands use `--data-dir DIR`, default `./data` in the current directory:

```
data/
├── processed/     # <id>.json per email, email_ids.txt, email_summary.json
├── attachments/   # <id>/<filename>
└── search_index/  # emails.sqlite3 (rebuilt from processed/ if missing)
```

From Python:

```python
from inbox_forge.core.search_engine import SearchEngine

results = SearchEngine('data/search_index').search('report', fields=['subject'])
```

## Test

```bash
uv sync --locked
uv run pytest
uv run ruff check && uv run ruff format --check
```

The tests run offline on the two fixture emails plus emails written in temporary directories.
CI runs these commands on Python 3.10-3.14 and the quick-start searches above.

## Boundaries

- Offline only: nothing reads from a mail server or makes network requests.
- Tested only on the fixture emails and synthetic ones, never on a real mail export.

MIT license.
