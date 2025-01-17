"""
JSON organizer for InboxForge.
Processes email data into structured JSON format with local attachment handling.
"""

from typing import Dict
from pathlib import Path
from datetime import datetime
from utils.email_parser import EmailParser
from utils.file_handler import FileHandler
import json

class JsonOrganizer:
    """Organizes email data into structured JSON format."""
    
    def __init__(self, base_dir: Path, exclude_html: bool = False):
        """
        Initialize JsonOrganizer.
        
        Args:
            base_dir: Base directory for all data storage
            exclude_html: Whether to exclude HTML content from processed output
        """
        self.base_dir = Path(base_dir)
        self.file_handler = FileHandler(base_dir)
        self.email_parser = EmailParser()
        self.exclude_html = exclude_html
    
    def process_email(self, eml_path: Path) -> Dict:
        """
        Process an email file into JSON format.
        
        Args:
            eml_path: Path to the .eml file
            
        Returns:
            dict: Processed email data
        """
        try:
            # Parse email
            raw_email_data = self.email_parser.parse_email_file(eml_path)
            
            # Process the body content based on HTML preference
            if self.exclude_html:
                content = raw_email_data['body'].get('plain', '')
            else:
                content = raw_email_data['body']
            
            # Create structured email data
            processed_email = {
                'id': raw_email_data['id'],
                'metadata': {
                    'sender': raw_email_data['sender'],
                    'recipient': raw_email_data['recipient'],
                    'subject': raw_email_data['subject'],
                    'date': raw_email_data['date'],
                    'original_file': str(eml_path.name),
                    'processed_date': datetime.now().isoformat()
                },
                'content': content,
                'attachments': []
            }
            
            # Process attachments
            for attachment in raw_email_data.get('attachments', []):
                # Save attachment locally
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
            
            # Save processed email data
            self.file_handler.save_processed_email(processed_email)
            self._update_summary(processed_email)
            
            return processed_email
            
        except Exception as e:
            print(f"\nError processing {eml_path.name}:")
            print(f"Exception: {str(e)}")
            print("Raw email data structure:", raw_email_data.keys() if 'raw_email_data' in locals() else "Not available")
            raise
    
    def get_processing_summary(self) -> Dict:
        """
        Get a summary of processed emails.
        
        Returns:
            dict: Summary information including total emails and last updated
        """
        summary_path = self.base_dir / 'data' / 'processed' / 'email_summary.json'
        
        try:
            if summary_path.exists():
                with open(summary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default summary if it doesn't exist
                summary = {
                    'total_emails': 0,
                    'last_updated': datetime.now().isoformat(),
                    'emails': []
                }
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2)
                return summary
                
        except Exception as e:
            print(f"Warning: Could not read summary file: {e}")
            return {
                'total_emails': 0,
                'last_updated': datetime.now().isoformat(),
                'emails': []
            }
    
    def _update_summary(self, email_data: Dict) -> None:
        """
        Update the email processing summary.
        
        Args:
            email_data: Processed email data to add to summary
        """
        summary_path = self.base_dir / 'data' / 'processed' / 'email_summary.json'
        summary = self.get_processing_summary()
        
        # Add new email to summary
        summary['total_emails'] += 1
        summary['last_updated'] = datetime.now().isoformat()
        summary['emails'].append({
            'id': email_data['id'],
            'subject': email_data['metadata']['subject'],
            'date': email_data['metadata']['date']
        })
        
        # Ensure directory exists
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save updated summary
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
