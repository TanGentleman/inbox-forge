# inbox-forge: implementation

## Requirements

- Python 3.10+ built with SQLite FTS5 (python.org, uv and most Linux builds are). A build without
  FTS5 fails with a `SearchError`.
- [uv](https://docs.astral.sh/uv/); CI uses uv 0.13.7.
- No runtime dependencies, no mail account, IMAP, API keys or network access.

To install the command outside a checkout: `pip install git+https://github.com/TanGentleman/inbox-forge`.

## Usage

```
inbox-forge ingest FOLDER [--data-dir DIR] [--include-html]
inbox-forge search QUERY [--in FIELDS] [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--data-dir DIR]
```

In a checkout, prefix both with `uv run`. On the two fixture emails,
`uv run inbox-forge search "from:alice" --after 2024-01-01` prints:

```
Found 1 matching emails:

Date: 2024-03-05 10:00
From: Alice Smith <alice@example.com>
To: "Doe, John" <john@example.com> bob@example.com Carol <carol@example.com>
Subject: Quarterly report
ID: 521daea0b43852fd
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
| 0 | done, including "No matching emails found." |
| 1 | `ingest` folder does not exist, or ingest failed |
| 2 | bad usage (no command, unknown command, missing argument), or an invalid `search` date or `--in` field (an error is printed) |

There are no environment variables. Both commands use `--data-dir DIR`, default `./data` in the
current directory:

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

## How it works

`src/inbox_forge/cli/ingest.py` finds the `.eml` files and passes each one to `JsonOrganizer`
(`core/json_organizer.py`), which parses it with `EmailParser` (`core/email_parser.py`), writes
`processed/<id>.json`, `email_ids.txt` and `email_summary.json`, and saves attachments through
`FileHandler` (`utils/file_handler.py`). The ingest CLI then indexes each stored email with
`SearchEngine.index_email`.

`core/search_engine.py` keeps the FTS5 table in `search_index/emails.sqlite3`. A new or missing
index fills itself from `processed/`. `cli/search.py` parses the `from:`/`to:`/`subject:` prefix
and the date filters and prints the results.

## Tests

```sh
uv sync --locked
uv run ruff check
uv run ruff format --check
uv run pytest
uv run inbox-forge ingest tests/fixtures
uv run inbox-forge search quarterly | grep "Quarterly report"
uv run inbox-forge search "from:alice" --after 2024-01-01 | grep "Quarterly report"
```

CI runs ruff once and the rest on Python 3.10-3.14. The tests run offline on the two fixture
emails in `tests/fixtures` plus emails written in temporary directories; `tests/test_cli.py`
covers the exit codes and the quick start.

## Limits

- Offline only: nothing reads from a mail server or makes network requests.
- Input is `.eml` files only.
- Tested only on the fixture emails and synthetic ones, never on a real mail export.
