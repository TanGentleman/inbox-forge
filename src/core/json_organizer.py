"""
JSON organizer for InboxForge.
Processes email data into structured JSON format with local attachment handling.
"""

from typing import Optional, Union
from pathlib import Path
from datetime import datetime
import json
import logging
from core.email_parser import DuplicateEmailError, EmailParser, ParsedEmail
from utils.file_handler import FileHandler
from config.paths import SUMMARY_FILE, EMAIL_IDS_FILE
from src.types.emails import ProcessedEmail, ProcessingSummary

logger = logging.getLogger(__name__)


class JsonOrganizer:
    """Organizes email data into structured JSON format."""

    def __init__(
        self,
        data_dir: Union[None, Path, str],
        exclude_html: bool = True,
        existing_ids: Optional[set[str]] = None,
    ):
        """
        Initialize the JSON organizer.

        Args:
            data_dir: Base directory for storing processed files
            exclude_html: Whether to exclude HTML content
            existing_ids: Optional set of existing email IDs to avoid duplicates
        """
        self.exclude_html = exclude_html
        self.email_ids_file = EMAIL_IDS_FILE
        self.existing_ids = self._load_existing_ids() if existing_ids is None else existing_ids
        self.email_parser = EmailParser(existing_ids=self.existing_ids)
        self.email_ids_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_handler = FileHandler(data_dir)

    def process_email(self, eml_path: Path) -> ProcessedEmail:
        """
        Process an email file into JSON format.

        Args:
            eml_path: Path to the .eml file

        Returns:
            ProcessedEmail: Structured email data, or None if duplicate email

        Raises:
            IOError: If email file cannot be read
            ValueError: If email data is invalid
        """
        raw_email_data = None
        try:
            raw_email_data = self.email_parser.parse_email_file(eml_path)
            processed_email = self._build_processed_email(raw_email_data, eml_path)
            self._process_attachments(processed_email, raw_email_data)

            # Save email and update tracking
            self.file_handler.save_processed_email(processed_email)
            self._update_summary(processed_email)
            self._track_email_id(processed_email['id'])

            logger.debug(
                f"Processed email {processed_email['id']}: {processed_email['metadata']['subject']}"
            )
            return processed_email

        except DuplicateEmailError:
            logger.warning(f'Skipping duplicate email: {eml_path.name}')
            return None
        except Exception as e:
            logger.error(f'Failed to process {eml_path.name}: {str(e)}')
            logger.debug(
                f'Raw email data structure: {raw_email_data.keys() if raw_email_data else "Not available"}'
            )
            raise

    def _track_email_id(self, email_id: str) -> None:
        """Track processed email ID in memory and on disk."""
        self.existing_ids.add(email_id)
        with open(self.email_ids_file, 'a') as f:
            f.write(f'{email_id}\n')

    def _build_processed_email(self, raw_data: ParsedEmail, eml_path: Path) -> ProcessedEmail:
        """Build processed email structure from raw data."""
        original_body = raw_data['body']
        content = ''
        if self.exclude_html:
            content = original_body.get('plain', '')
        else:
            logger.warning('HTML content will be included')
            # concatenate plain and html
            content = original_body.get('plain', '') + original_body.get('html', '')

        content = str(content).strip()

        return {
            'id': raw_data['id'],
            'metadata': {
                'sender': raw_data['sender'],
                'recipient': raw_data['recipient'],
                'subject': raw_data['subject'],
                'date': raw_data['date'],
                'original_file': eml_path.name,
                'processed_date': datetime.now().isoformat(),
            },
            'content': content,
            'attachments': [],
        }

    def _process_attachments(self, processed_email: ProcessedEmail, raw_data: ParsedEmail) -> None:
        """Process and store email attachments."""
        for attachment in raw_data.get('attachments', []):
            location = self.file_handler.save_attachment(processed_email['id'], attachment)
            processed_email['attachments'].append(
                {
                    'name': attachment['name'],
                    'type': attachment['type'],
                    'size': attachment['size'],
                    'location': location,
                }
            )

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
            logger.warning(f'Could not read summary file: {e}')
            return self._create_default_summary()

    def _create_default_summary(self) -> ProcessingSummary:
        """Create and save default summary structure."""
        summary: ProcessingSummary = {
            'total_emails': 0,
            'last_updated': datetime.now().isoformat(),
            'emails': [],
        }

        try:
            SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            logger.warning(f'Failed to save default summary: {e}')

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
            summary['emails'].append(
                {
                    'id': email_data['id'],
                    'subject': email_data['metadata']['subject'],
                    'date': email_data['metadata']['date'],
                }
            )

            with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)

        except Exception as e:
            logger.error(f'Failed to update summary: {e}')

    def _load_existing_ids(self) -> set[str]:
        """Load existing email IDs from storage."""
        if not self.email_ids_file.exists():
            return set()

        try:
            with open(self.email_ids_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            logger.error(f'Failed to load existing IDs: {e}')
            return set()

    def get_email_ids(self) -> set[str]:
        """Get the set of all processed email IDs."""
        return self.existing_ids.copy()
