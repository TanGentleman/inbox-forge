# inbox-forge

Make a folder of exported emails searchable, offline. inbox-forge reads `.eml` files
(Gmail Takeout, Apple Mail, Thunderbird exports), writes one JSON file per email, saves
attachments, and builds a local full-text index. No mail account, IMAP or API keys.

## Install

```bash
pip install git+https://github.com/TanGentleman/inbox-forge
```

Python 3.10 or newer, with SQLite FTS5 (included in python.org, uv and most Linux
builds). No other dependencies.

## Try it

From a clone, on the two sample emails in `tests/fixtures`:

```bash
inbox-forge ingest tests/fixtures
inbox-forge search "quarterly"
inbox-forge search "from:alice" --after 2024-01-01
```

```
Found 1 matching emails:

Date: 2024-03-05 10:00
From: Alice Smith <alice@example.com>
To: "Doe, John" <john@example.com> bob@example.com Carol <carol@example.com>
Subject: Quarterly report
ID: 521daea0b43852fd
```

Running `ingest` again skips emails it has already seen, so you can re-run it on a growing
folder.

## Search

- Words match subject, body, sender and recipients: `inbox-forge search "lunch friday"`.
- Prefix one field: `from:`, `to:` or `subject:`. Or pick fields with
  `--in subject,content,sender,recipient`.
- `AND`, `OR`, `NOT`, `"exact phrase"` and `meet*` work.
- Date range: `--after 2024-01-01 --before 2024-12-31`.

## Options and output

`ingest` and `search` both take `--data-dir DIR` (default `./data`). `ingest
--include-html` also indexes the HTML part of each email.

```
data/
├── processed/     # <id>.json per email, email_ids.txt, email_summary.json
├── attachments/   # <id>/<filename>
└── search_index/  # SQLite FTS5 index (emails.sqlite3)
```

From Python:

```python
from inbox_forge.core.search_engine import SearchEngine

results = SearchEngine('data/search_index').search('report', fields=['subject'])
```

## Develop

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
```

MIT license.
