"""
Search engine for InboxForge emails using Whoosh.

Provides full-text search capabilities across email content and metadata with optional date filtering.

Example usage:
    # Basic search
    search_engine = SearchEngine(base_dir)
    results = search_engine.search("meeting notes")
    
    # Advanced search with filters
    results = search_engine.search(
        query="project update",
        fields=["subject", "body"], 
        date_range=(start_date, end_date)
    )
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from whoosh import index
from whoosh.fields import DATETIME, ID, TEXT, Schema
from whoosh.qparser import MultifieldParser
from whoosh.query import And, DateRange, Every

from src.classes.json_organizer import ProcessedEmail
from src.paths import SEARCH_INDEX_DIR
from src.types.errors import SearchError

logger = logging.getLogger(__name__)

class SearchEngine:
    """Email search engine using Whoosh for full-text search."""
    
    # Fields available for searching
    SEARCHABLE_FIELDS = [
        'subject',
        'content', 
        'sender',
        'recipient'
    ]
    
    # Maximum search results (None for unlimited)
    MAX_RESULTS = None
    
    def __init__(self, base_dir: Union[str, Path]) -> None:
        """
        Initialize the search engine.
        
        Args:
            base_dir: Base directory for the application
            
        Raises:
            SearchError: If index initialization fails
        """
        self.index_dir = SEARCH_INDEX_DIR
        self.schema = Schema(
            id=ID(stored=True, unique=True),
            sender=TEXT(stored=True),
            recipient=TEXT(stored=True), 
            subject=TEXT(stored=True),
            body=TEXT,
            date=DATETIME(stored=True)
        )
        self._ensure_index()
    
    def _ensure_index(self) -> None:
        """
        Create or load the search index.
        
        Raises:
            SearchError: If index creation/loading fails
        """
        try:
            if not self.index_dir.exists():
                self.index_dir.mkdir(parents=True)
                self.ix = index.create_in(str(self.index_dir), self.schema)
            else:
                self.ix = index.open_dir(str(self.index_dir))
        except Exception as e:
            logger.error("Failed to initialize index: %s", e)
            raise SearchError(f"Index initialization failed: {e}")
    
    def index_email(self, email_data: ProcessedEmail) -> None:
        """
        Add an email to the search index.
        
        Args:
            email_data: Processed email data to index
            
        Raises:
            ValueError: If required email fields are missing
            SearchError: If indexing fails
        """
        self._validate_email_data(email_data)
        
        try:
            writer = self.ix.writer()

            writer.update_document(
                id=email_data['id'],
                sender=email_data['metadata']['sender'],
                recipient=' '.join(email_data['metadata']['recipient']),
                subject=email_data['metadata']['subject'],
                body=email_data['content'],
                date=datetime.fromisoformat(email_data['metadata']['date'])
            )
            writer.commit()
            
        except Exception as e:
            logger.error("Failed to index email %s: %s", email_data.get('id'), e)
            raise SearchError(f"Failed to index email: {e}")
    
    def _validate_email_data(self, email_data: ProcessedEmail) -> None:
        """Validate required email fields are present."""
        required_fields = ['id', 'metadata', 'content']
        if missing := [f for f in required_fields if f not in email_data]:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict]:
        """
        Search indexed emails with optional filters.
        
        Args:
            query: Search query string (empty string returns all emails within date range)
            fields: Specific fields to search (defaults to all fields)
            date_range: Optional (start_date, end_date) tuple for filtering
            
        Returns:
            List of matching email dictionaries
            
        Raises:
            SearchError: If search fails
        """
        search_fields = fields or self.SEARCHABLE_FIELDS
            
        try:
            with self.ix.searcher() as searcher:
                search_query = self._build_search_query(query, search_fields, date_range)
                results = searcher.search(search_query, limit=self.MAX_RESULTS)
                return [dict(result) for result in results]
                
        except Exception as e:
            logger.error("Search failed: %s", e)
            raise SearchError(f"Search operation failed: {e}")
            
    def _validate_search_params(self, query: str, fields: Optional[List[str]]) -> None:
        """Validate search parameters."""
        if fields and (invalid := set(fields) - set(self.SEARCHABLE_FIELDS)):
            raise ValueError(f"Invalid search fields: {', '.join(invalid)}")
            
    def _build_search_query(self, query: str, fields: List[str], date_range: Optional[Tuple[datetime, datetime]]):
        """Build the search query with filters."""
        # Start with a query that matches everything
        final_query = Every()

        # Add text search if query is not empty
        if query.strip():
            final_query = MultifieldParser(fields, self.ix.schema).parse(query)
        
        # Add date range filter if provided
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
