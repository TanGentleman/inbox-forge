"""
Full-text search over processed emails with SQLite FTS5 (Python standard library).

Example:
    engine = SearchEngine()
    results = engine.search('project update', fields=['subject', 'content'])
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

from inbox_forge.core.json_organizer import ProcessedEmail
from inbox_forge.types.errors import SearchError
from inbox_forge.utils.file_handler import DATA_DIR

SearchableField = Literal['subject', 'content', 'sender', 'recipient']
RequiredField = Literal['id', 'metadata', 'content']
DateRangeFilter = tuple[datetime | None, datetime | None]

logger = logging.getLogger(__name__)

TOKEN = re.compile(r'"[^"]*"?|\S+')
OPERATORS = {'AND', 'OR', 'NOT'}


class SearchEngine:
    """Email search engine with field and date filters."""

    SEARCHABLE_FIELDS: list[SearchableField] = ['subject', 'content', 'sender', 'recipient']
    REQUIRED_FIELDS_TO_INDEX: list[RequiredField] = ['id', 'metadata', 'content']
    MAX_RESULTS = 100

    def __init__(self, index_dir: None | str | Path = None) -> None:
        """Open the index in index_dir, creating it from processed/ if it is new."""
        self.index_dir = Path(index_dir) if index_dir else DATA_DIR / 'search_index'
        db_path = self.index_dir / 'emails.sqlite3'
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            is_new = not db_path.exists()
            self.db = sqlite3.connect(db_path)
            self.db.execute(
                'CREATE VIRTUAL TABLE IF NOT EXISTS emails USING fts5('
                'id UNINDEXED, sender, recipient, subject, content, date UNINDEXED)'
            )
        except sqlite3.Error as e:
            raise SearchError(f'Index initialization failed: {e}') from e
        if is_new:
            self._index_processed(self.index_dir.parent / 'processed')

    def _index_processed(self, processed_dir: Path) -> None:
        """Index emails already in processed/, e.g. after an upgrade from the Whoosh index."""
        files = [p for p in processed_dir.glob('*.json') if p.name != 'email_summary.json']
        for path in files:
            self.index_email(json.loads(path.read_text(encoding='utf-8')))
        if files:
            logger.info('Indexed %d previously processed emails', len(files))

    def index_email(self, email_data: ProcessedEmail) -> None:
        """
        Add or replace an email in the index.

        Raises:
            ValueError: If required fields missing
            SearchError: If indexing fails
        """
        if missing := [f for f in self.REQUIRED_FIELDS_TO_INDEX if f not in email_data]:
            raise ValueError(f'Missing required fields: {", ".join(missing)}')

        meta = email_data['metadata']
        rowid = int(email_data['id'][:15], 16)
        try:
            with self.db:
                self.db.execute('DELETE FROM emails WHERE rowid = ?', (rowid,))
                self.db.execute(
                    'INSERT INTO emails (rowid, id, sender, recipient, subject, content, date) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (
                        rowid,
                        email_data['id'],
                        meta['sender'],
                        ' '.join(meta['recipient']),
                        meta['subject'],
                        email_data['content'],
                        meta['date'],
                    ),
                )
        except sqlite3.Error as e:
            raise SearchError(f'Failed to index email: {e}') from e

    def search(
        self,
        query: str,
        fields: list[SearchableField] | None = None,
        date_range: DateRangeFilter | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        """Search emails with optional field and date filters.

        Args:
            query: Words, "phrases", prefix* terms and AND/OR/NOT (empty matches all)
            fields: Fields to search (defaults to all searchable fields)
            date_range: (start, end) datetimes, either may be None; inclusive
            max_results: Maximum number of results (defaults to MAX_RESULTS)

        Returns:
            Dicts with id, sender, recipient, subject and date (datetime), best match first

        Raises:
            ValueError: If invalid search fields specified or max_results < 1
            SearchError: If search operation fails
        """
        result_limit = max_results or self.MAX_RESULTS
        if result_limit < 1:
            raise ValueError('max_results must be greater than 0')

        search_fields = fields if fields else self.SEARCHABLE_FIELDS
        invalid_fields = [f for f in search_fields if f not in self.SEARCHABLE_FIELDS]
        if invalid_fields:
            raise ValueError(f'Invalid search fields: {", ".join(invalid_fields)}')

        try:
            return self._run(query, search_fields, date_range, result_limit, strict=True)
        except sqlite3.OperationalError:
            # Unbalanced operators such as a leading NOT: retry with the words alone.
            try:
                return self._run(query, search_fields, date_range, result_limit, strict=False)
            except sqlite3.Error as e:
                raise SearchError(f'Search operation failed: {e}') from e
        except sqlite3.Error as e:
            raise SearchError(f'Search operation failed: {e}') from e

    def _run(self, query, fields, date_range, limit, strict):
        where, params = [], []
        expression = _match_expression(query, strict)
        if query.strip() and not expression:
            return []
        if expression:
            where.append('emails MATCH ?')
            params.append(f'{{{" ".join(fields)}}} : ({expression})')
        start, end = date_range or (None, None)
        # Compare wall-clock time as written in the email, ignoring its UTC offset.
        if start:
            where.append('substr(date, 1, 19) >= ?')
            params.append(start.replace(tzinfo=None).isoformat())
        if end:
            where.append('substr(date, 1, 19) <= ?')
            params.append(end.replace(tzinfo=None).isoformat())

        sql = 'SELECT id, sender, recipient, subject, date FROM emails'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY rank' if expression else ' ORDER BY date'
        rows = self.db.execute(sql + ' LIMIT ?', (*params, limit)).fetchall()
        return [
            {
                'id': id_,
                'sender': sender,
                'recipient': recipient,
                'subject': subject,
                'date': datetime.fromisoformat(date),
            }
            for id_, sender, recipient, subject, date in rows
        ]


def _match_expression(query: str, strict: bool) -> str:
    """Turn a user query into an FTS5 expression, quoting every term."""
    parts = []
    for token in TOKEN.findall(query):
        if token in OPERATORS:
            if strict:
                parts.append(token)
            continue
        prefix = strict and token.endswith('*') and not token.startswith('"')
        word = token.strip('"').rstrip('*') if prefix else token.strip('"')
        if word.strip():
            parts.append('"' + word.replace('"', '') + '"' + ('*' if prefix else ''))
    return ' '.join(parts)
