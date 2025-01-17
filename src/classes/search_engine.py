"""
Search engine for InboxForge.
Provides indexing and searching capabilities for processed emails.
"""

from typing import List, Dict, Union
from pathlib import Path
import json
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import DateRange
from datetime import datetime
from src.paths import SEARCH_INDEX_DIR

class SearchEngine:
    """Provides email search functionality using Whoosh."""
    
    def __init__(self, base_dir: Path):
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
        """Create or load the search index."""
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True)
            self.ix = index.create_in(str(self.index_dir), self.schema)
        else:
            self.ix = index.open_dir(str(self.index_dir))
    
    def index_email(self, email_data: Dict) -> None:
        """
        Index an email for searching.
        
        Args:
            email_data: Processed email data dictionary
        """
        writer = self.ix.writer()
        
        # Combine plain and HTML body for indexing
        body_text = (email_data['body'].get('plain', '') + ' ' + 
                    email_data['body'].get('html', ''))
        
        writer.update_document(
            id=email_data['id'],
            sender=email_data['sender'],
            recipient=' '.join(email_data['recipient']),
            subject=email_data['subject'],
            body=body_text,
            date=datetime.fromisoformat(email_data['date'])
        )
        writer.commit()
    
    def search(self, 
               query: str, 
               fields: List[str] = None,
               date_range: tuple = None) -> List[Dict]:
        """
        Search indexed emails.
        
        Args:
            query: Search query string
            fields: List of fields to search in
            date_range: Optional tuple of (start_date, end_date)
            
        Returns:
            list: List of matching email data
        """
        if fields is None:
            fields = ['subject', 'body', 'sender', 'recipient']
        
        with self.ix.searcher() as searcher:
            query_parser = MultifieldParser(fields, self.ix.schema)
            parsed_query = query_parser.parse(query)
            
            if date_range:
                start_date, end_date = date_range
                date_query = DateRange('date', start_date, end_date)
                parsed_query = parsed_query & date_query
            
            results = searcher.search(parsed_query, limit=None)
            return [dict(result) for result in results] 