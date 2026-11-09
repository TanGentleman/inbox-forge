# inbox-forge

Makes a folder of exported `.eml` files searchable offline: one JSON file per email, saved
attachments, and a SQLite FTS5 index. No mail account or network.

```bash
git clone https://github.com/TanGentleman/inbox-forge && cd inbox-forge
uv sync --locked
uv run inbox-forge ingest tests/fixtures && uv run inbox-forge search quarterly
```

Needs Python 3.10+ with SQLite FTS5 and [uv](https://docs.astral.sh/uv/). Details:
[IMPLEMENTATION.md](IMPLEMENTATION.md), [ROADMAP.md](ROADMAP.md).

MIT licensed.
