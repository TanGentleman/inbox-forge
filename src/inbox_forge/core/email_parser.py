"""
Email parser utility for InboxForge.
Parses .eml files into structured data with metadata, content and attachments.
"""

import hashlib
import logging
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

from inbox_forge.types.emails import EmailAttachment, EmailBody, ParsedEmail
from inbox_forge.types.errors import DuplicateEmailError

logger = logging.getLogger(__name__)


class EmailParser:
    """Parses .eml files into structured data."""

    def __init__(self, existing_ids: set[str] | None = None):
        """
        Initialize with default values and email parser.

        Args:
            existing_ids: Optional set of existing email IDs to avoid duplicates
        """
        self.parser = BytesParser(policy=policy.default)
        self.default_date = datetime.now().isoformat()
        self.default_values = {
            'subject': '[No Subject]',
            'sender': '[No Sender]',
            'recipients': ['[No Recipients]'],
            'body': '[Could not extract email body]',
        }
        self.existing_ids = existing_ids if existing_ids is not None else set()

    def _generate_email_id(self, content: bytes) -> str:
        """
        Generate a unique ID for an email based on its content.

        Args:
            content: Raw email content bytes

        Returns:
            str: 16-character hexadecimal ID
        """
        return hashlib.sha256(content).hexdigest()[:16]

    def parse_email_file(self, eml_path: str | Path) -> ParsedEmail:
        """
        Parse an .eml file into structured data.

        Args:
            eml_path: Path to the .eml file

        Returns:
            ParsedEmail containing all email data and content

        Raises:
            IOError: If file cannot be read
            email.errors.MessageParseError: If parsing fails
            DuplicateEmailError: If email is a duplicate
        """
        try:
            content = Path(eml_path).read_bytes()
            email_id = self._generate_email_id(content)

            if email_id in self.existing_ids:
                logger.debug('Duplicate email detected: %s', email_id)
                raise DuplicateEmailError(f'Email with ID {email_id} already exists')

            msg = self.parser.parsebytes(content)

            email_data = {
                'id': email_id,
                'sender': self._get_header(msg, 'from', self.default_values['sender']),
                'recipient': self._get_recipients(msg),
                'subject': self._get_header(msg, 'subject', self.default_values['subject']),
                'date': self._get_date(msg.get('date')),
                'body': self._get_body(msg),
                'attachments': self._get_attachments(msg),
            }

            logger.debug(
                'Parsed email - Subject: %s, From: %s, Date: %s',
                email_data['subject'],
                email_data['sender'],
                email_data['date'],
            )

            return email_data

        except DuplicateEmailError:
            raise
        except Exception as e:
            logger.error('Failed to parse %s: %s', eml_path, str(e))
            raise

    def _get_header(self, msg: EmailMessage, header: str, default: str) -> str:
        """Safely extract an email header with fallback."""
        try:
            value = msg.get(header, '')
            return value if value else default
        except Exception as e:
            logger.warning('Failed to get %s: %s', header, e)
            return default

    def _get_recipients(self, msg: EmailMessage) -> list[str]:
        """Extract all recipient addresses from To, CC and BCC fields."""
        recipients = []
        try:
            for field in ['to', 'cc', 'bcc']:
                for header in msg.get_all(field, []):
                    recipients.extend(str(addr) for addr in header.addresses)
            return recipients or self.default_values['recipients']
        except Exception as e:
            logger.warning('Failed to get recipients: %s', e)
            return self.default_values['recipients']

    def _get_date(self, date_str: str | None) -> str:
        """Convert email date to ISO format."""
        if not date_str:
            return self.default_date

        try:
            return parsedate_to_datetime(date_str).isoformat()
        except Exception as e:
            logger.warning('Failed to parse date: %s', e)
            return self.default_date

    def _get_body(self, msg: EmailMessage) -> EmailBody:
        """Extract plain text and HTML body content."""
        body = {'plain': None, 'html': None}

        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_maintype() == 'text' and not part.get_filename():
                        self._extract_text_content(part, body)
            else:
                self._extract_text_content(msg, body)

            if not body['plain']:
                text = html_to_text(body['html']) if body['html'] else ''
                body['plain'] = text or self.default_values['body']

            return body

        except Exception as e:
            logger.warning('Failed to extract body: %s', e)
            return {'plain': self.default_values['body'], 'html': None}

    def _extract_text_content(self, part: EmailMessage, body: EmailBody) -> None:
        """Extract text content from a message part."""
        payload = part.get_payload(decode=True)
        try:
            content = payload.decode(part.get_content_charset() or 'utf-8')
        except (LookupError, UnicodeDecodeError):
            content = payload.decode('latin-1')

        if part.get_content_subtype() == 'plain':
            body['plain'] = content
        elif part.get_content_subtype() == 'html':
            body['html'] = content
        else:
            logger.warning('Unhandled content type: %s', part.get_content_type())

    def _get_attachments(self, msg: EmailMessage) -> list[EmailAttachment]:
        """Extract all email attachments."""
        attachments = []

        try:
            for part in msg.walk():
                if part.get_content_maintype() != 'multipart' and part.get_filename():
                    content = part.get_payload(decode=True)
                    attachments.append(
                        {
                            'name': part.get_filename(),
                            'type': part.get_content_type(),
                            'size': len(content),
                            'content': content,
                        }
                    )
        except Exception as e:
            logger.warning('Failed to extract attachments: %s', e)

        return attachments


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.chunks.append(data)


def html_to_text(html: str) -> str:
    """Visible text of an HTML document, whitespace collapsed."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return ' '.join(' '.join(parser.chunks).split())
