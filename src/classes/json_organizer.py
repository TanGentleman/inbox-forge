"""
JSON organizer for InboxForge.
Processes email data into structured JSON format with local attachment handling.
"""

from typing import Dict, TypedDict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import logging
from src.classes.email_parser import DuplicateEmailError, EmailParser, ParsedEmail
from src.classes.file_handler import FileHandler
from src.paths import SUMMARY_FILE
from src.types.emails import ProcessedEmail, ProcessingSummary

class JsonOrganizer:
    """Organizes email data into structured JSON format."""
    
    def __init__(self, base_dir: Path, exclude_html: bool = True, existing_ids: Optional[set[str]] = None):
        """
        Initialize the JSON organizer.
        
        Args:
            base_dir: Base directory for storing processed files
            exclude_html: Whether to exclude HTML content
            existing_ids: Optional set of existing email IDs to avoid duplicates
        """
        self.base_dir = Path(base_dir)
        self.exclude_html = exclude_html
        self.email_ids_file = self.base_dir / 'data' / 'email_ids.txt'
        self.existing_ids = self._load_existing_ids() if existing_ids is None else existing_ids
        self.email_parser = EmailParser(existing_ids=self.existing_ids)
        self.email_ids_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_handler = FileHandler(self.base_dir)
    
    def process_email(self, eml_path: Path) -> ProcessedEmail:
        """
        Process an email file into JSON format.
        
        Args:
            eml_path: Path to the .eml file
            
        Returns:
            ProcessedEmail: Structured email data
            
        Raises:
            IOError: If email file cannot be read
            ValueError: If email data is invalid
        """
        try:
            raw_email_data = self.email_parser.parse_email_file(eml_path)
            
            processed_email = self._build_processed_email(raw_email_data, eml_path)
            self._process_attachments(processed_email, raw_email_data)
            
            self.file_handler.save_processed_email(processed_email)
            self._update_summary(processed_email)
            
            # Add email ID to tracking and append to file
            self.existing_ids.add(processed_email['id'])
            with open(self.email_ids_file, 'a') as f:
                f.write(f"{processed_email['id']}\n")
            
            logging.debug(
                "Processed email %s: %s", 
                processed_email['id'],
                processed_email['metadata']['subject']
            )
            
            return processed_email
        except DuplicateEmailError:
            logging.warning("Skipping duplicate email: %s", eml_path.name)
            return None
        except Exception as e:
            logging.error("Failed to process %s: %s", eml_path.name, str(e))
            logging.debug(
                "Raw email data structure: %s", 
                raw_email_data.keys() if 'raw_email_data' in locals() else "Not available"
            )
            raise
    
    def _build_processed_email(self, raw_data: ParsedEmail, eml_path: Path) -> ProcessedEmail:
        """Build processed email structure from raw data."""
        body = raw_data['body'].get('plain', '') if self.exclude_html else raw_data['body']
        
        return {
            'id': raw_data['id'],
            'metadata': {
                'sender': raw_data['sender'],
                'recipient': raw_data['recipient'], 
                'subject': raw_data['subject'],
                'date': raw_data['date'],
                'original_file': str(eml_path.name),
                'processed_date': datetime.now().isoformat()
            },
            'body': body,
            'attachments': []
        }
    
    def _process_attachments(self, processed_email: ProcessedEmail, raw_data: ParsedEmail) -> None:
        """Process and store email attachments."""
        for attachment in raw_data.get('attachments', []):
            location = self.file_handler.save_attachment(
                processed_email['id'],
                attachment
            )
            processed_email['attachments'].append({
                'name': attachment['name'],
                'type': attachment['type'],
                'size': attachment['size'],
                'location': location
            })
    
    def get_processing_summary(self) -> ProcessingSummary:
        """
        Get a summary of processed emails.
        
        Returns:
            ProcessingSummary: Summary information including total emails and last updated
        """
        try:
            if SUMMARY_FILE.exists():
                with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            return self._create_default_summary()
                
        except Exception as e:
            logging.warning("Could not read summary file: %s", e)
            return self._create_default_summary()
    
    def _create_default_summary(self) -> ProcessingSummary:
        """Create and save default summary structure."""
        summary: ProcessingSummary = {
            'total_emails': 0,
            'last_updated': datetime.now().isoformat(),
            'emails': []
        }
        
        try:
            SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            logging.warning("Failed to save default summary: %s", e)
            
        return summary
    
    def _update_summary(self, email_data: ProcessedEmail) -> None:
        """
        Update the email processing summary.
        
        Args:
            email_data: Processed email data to add to summary
        """
        try:
            summary = self.get_processing_summary()
            
            summary['total_emails'] += 1
            summary['last_updated'] = datetime.now().isoformat()
            summary['emails'].append({
                'id': email_data['id'],
                'subject': email_data['metadata']['subject'],
                'date': email_data['metadata']['date']
            })
            
            with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            logging.error("Failed to update summary: %s", e)

    def _load_existing_ids(self) -> set[str]:
        """Load existing email IDs from storage."""
        if not self.email_ids_file.exists():
            return set()
            
        try:
            with open(self.email_ids_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            logging.error("Failed to load existing IDs: %s", e)
            return set()
    
    def get_email_ids(self) -> set[str]:
        """Get the set of all processed email IDs."""
        return self.existing_ids.copy()
