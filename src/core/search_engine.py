"""
Search engine for InboxForge emails using Whoosh.

Provides full-text search across email content and metadata with optional filters.

Example:
    engine = SearchEngine()
    results = engine.search(
        query="project update", 
        fields=["subject", "content"],
        date_range=(start_date, end_date)
    )
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Literal, Tuple

from whoosh import index
from whoosh.fields import DATETIME, ID, TEXT, Schema
from whoosh.qparser import MultifieldParser
from whoosh.query import And, DateRange, Every

from src.config.settings import DEFAULT_MAX_RESULTS
from src.core.json_organizer import ProcessedEmail
from src.config.paths import SEARCH_INDEX_DIR
from src.types.errors import SearchError

# Type aliases for clarity
SearchableField = Literal["subject", "content", "sender", "recipient"]
RequiredField = Literal["id", "metadata", "content"]
DateRangeFilter = Tuple[Optional[datetime], Optional[datetime]]

logger = logging.getLogger(__name__)


class SearchEngine:
    """Email search engine using Whoosh for full-text search with filtering."""

    SEARCHABLE_FIELDS: List[SearchableField] = ["subject", "content", "sender", "recipient"]
    REQUIRED_FIELDS_TO_INDEX: List[RequiredField] = ["id", "metadata", "content"]
    MAX_RESULTS = DEFAULT_MAX_RESULTS

    def __init__(self, index_dir: Union[None, str, Path] = None) -> None:
        """Initialize with optional custom index directory."""
        self.index_dir = Path(index_dir) if index_dir else SEARCH_INDEX_DIR
        self.schema = Schema(
            id=ID(stored=True, unique=True),
            sender=TEXT(stored=True),
            recipient=TEXT(stored=True), 
            subject=TEXT(stored=True),
            content=TEXT,
            date=DATETIME(stored=True),
        )
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create or load the search index."""
        try:
            if not self.index_dir.exists():
                self.index_dir.mkdir(parents=True)
                self.ix = index.create_in(str(self.index_dir), self.schema)
            else:
                self.ix = index.open_dir(str(self.index_dir))
        except Exception as e:
            logger.error('Failed to initialize index: %s', e)
            raise SearchError(f'Index initialization failed: {e}')

    def index_email(self, email_data: ProcessedEmail) -> None:
        """
        Add/update email in search index.

        Raises:
            ValueError: If required fields missing
            SearchError: If indexing fails
        """
        if missing := [f for f in self.REQUIRED_FIELDS_TO_INDEX if f not in email_data]:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        try:
            writer = self.ix.writer()
            writer.update_document(
                id=email_data['id'],
                sender=email_data['metadata']['sender'],
                recipient=' '.join(email_data['metadata']['recipient']),
                subject=email_data['metadata']['subject'],
                content=email_data['content'],
                date=datetime.fromisoformat(email_data['metadata']['date']),
            )
            writer.commit()
        except Exception as e:
            logger.error('Failed to index email %s: %s', email_data.get('id'), e)
            raise SearchError(f'Failed to index email: {e}')

    def search(
        self,
        query: str,
        fields: Optional[List[SearchableField]] = None,
        date_range: Optional[DateRangeFilter] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict]:
        """Search emails with optional field and date filters.

        Args:
            query: Search terms (empty string matches all emails)
            fields: Optional list of fields to search (defaults to all searchable fields)
            date_range: Optional tuple of (start_date, end_date) to filter by date
            max_results: Maximum number of results to return (defaults to self.MAX_RESULTS)

        Returns:
            List of matching email documents

        Raises:
            ValueError: If invalid search fields specified or max_results < 1
            SearchError: If search operation fails
        """
        # Validate max_results
        result_limit = max_results or self.MAX_RESULTS
        if result_limit < 1:
            raise ValueError("max_results must be greater than 0")

        # Validate and prepare search fields
        search_fields = fields if fields else self.SEARCHABLE_FIELDS
        invalid_fields = [f for f in search_fields if f not in self.SEARCHABLE_FIELDS]
        if invalid_fields:
            raise ValueError(f"Invalid search fields: {', '.join(invalid_fields)}")

        try:
            with self.ix.searcher() as searcher:
                query = self._build_query(query, search_fields, date_range)
                results = searcher.search(query, limit=result_limit)
                return [dict(result) for result in results]
        except Exception as e:
            logger.error("Search failed: %s", e)
            raise SearchError(f"Search operation failed: {e}")

    def _build_query(self, query: str, fields: List[SearchableField], date_range: Optional[DateRangeFilter]):
        """Build combined text and date filter query."""
        final_query = Every()

        if query.strip():
            final_query = MultifieldParser(fields, self.ix.schema).parse(query)

        if date_range:
            start_date, end_date = date_range
            if start_date and end_date:
                date_query = DateRange('date', start_date, end_date)
            elif start_date:
                date_query = DateRange('date', start_date, None)
            elif end_date:
                date_query = DateRange('date', None, end_date)
            final_query = And([final_query, date_query])

        return final_query
