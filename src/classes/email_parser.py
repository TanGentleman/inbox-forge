"""
Email parser utility for InboxForge.
Handles parsing of .eml files into structured data.
"""

import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, TypedDict
import hashlib
import logging

logger = logging.getLogger(__name__)

class EmailBody(TypedDict):
    """Schema for email body content."""
    plain: str
    html: str

class EmailAttachment(TypedDict):
    """Schema for email attachment metadata."""
    name: str
    type: str
    size: int
    content: bytes

class ParsedEmail(TypedDict):
    """Schema for parsed email data."""
    id: str
    sender: str
    recipient: List[str]
    subject: str
    date: str
    body: EmailBody
    attachments: List[EmailAttachment]

class EmailParser:
    """Parses .eml files and extracts structured data."""
    
    def __init__(self):
        """Initialize parser with default email policy."""
        self.parser = BytesParser(policy=policy.default)
        self.default_date = datetime.now().isoformat()
        self.default_values = {
            'subject': '[No Subject]',
            'sender': '[No Sender]',
            'recipients': ['[No Recipients]'],
            'body': '[Could not extract email body]'
        }
    
    def generate_email_id(self, content: bytes) -> str:
        """Generate a unique 16-character hexadecimal ID from email content."""
        return hashlib.sha256(content).hexdigest()[:16]
    
    def parse_email_file(self, eml_path: Union[str, Path]) -> ParsedEmail:
        """
        Parse an .eml file into structured data.
        
        Args:
            eml_path: Path to the .eml file
            
        Returns:
            ParsedEmail: Structured email data including metadata and content
                
        Raises:
            IOError: If file cannot be read
            email.errors.MessageParseError: If email parsing fails
        """
        try:
            content = self._read_email_file(eml_path)
            email_msg = self.parser.parsebytes(content)
            
            email_data = self._build_email_data(content, email_msg)
            
            logger.debug(
                "Parsed email - Subject: %s, Sender: %s, Date: %s",
                email_data['subject'], email_data['sender'], email_data['date']
            )
            
            return email_data
            
        except Exception as e:
            logger.error("Failed to parse %s: %s", eml_path, str(e))
            raise
    
    def _read_email_file(self, path: Union[str, Path]) -> bytes:
        """Read email file content."""
        with open(path, 'rb') as f:
            return f.read()
            
    def _build_email_data(self, content: bytes, msg: email.message.EmailMessage) -> ParsedEmail:
        """Construct ParsedEmail from raw content and parsed message."""
        return {
            'id': self.generate_email_id(content),
            'sender': self._extract_sender(msg),
            'recipient': self._extract_recipients(msg),
            'subject': self._extract_subject(msg),
            'date': self._parse_date(msg.get('date')),
            'body': self._extract_body(msg),
            'attachments': self._extract_attachments(msg)
        }
    
    def _extract_subject(self, msg: email.message.EmailMessage) -> str:
        """Extract email subject with fallback."""
        try:
            subject = msg.get('subject', '')
            return subject if subject else self.default_values['subject']
        except Exception as e:
            logger.warning("Subject extraction failed: %s", e)
            return self.default_values['subject']
    
    def _extract_sender(self, msg: email.message.EmailMessage) -> str:
        """Extract sender address with fallback."""
        try:
            return msg.get('from', self.default_values['sender'])
        except Exception as e:
            logger.warning("Sender extraction failed: %s", e)
            return self.default_values['sender']
    
    def _extract_recipients(self, msg: email.message.EmailMessage) -> List[str]:
        """Extract all recipient addresses."""
        recipients = []
        try:
            for header in ['to', 'cc', 'bcc']:
                if value := msg.get(header):
                    recipients.extend(addr.strip() for addr in value.split(','))
            return recipients or self.default_values['recipients']
        except Exception as e:
            logger.warning("Recipient extraction failed: %s", e)
            return self.default_values['recipients']
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse email date to ISO format with fallback."""
        if not date_str:
            return self.default_date
            
        try:
            return email.utils.parsedate_to_datetime(date_str).isoformat()
        except Exception as e:
            logger.warning("Date parsing failed: %s", e)
            return self.default_date
    
    def _extract_body(self, msg: email.message.EmailMessage) -> EmailBody:
        """Extract email body content."""
        body: EmailBody = {'plain': '', 'html': ''}
        
        try:
            if msg.is_multipart():
                self._process_multipart(msg, body)
            else:
                self._process_singlepart(msg, body)
                
            self._normalize_body_content(body)
                
        except Exception as e:
            logger.warning("Body extraction failed: %s", e)
            body['plain'] = self.default_values['body']
            body['html'] = ''
            
        return body
    
    def _process_multipart(self, msg: email.message.EmailMessage, body: EmailBody) -> None:
        """Process multipart email content."""
        for part in msg.walk():
            if part.get_content_maintype() == 'text' and not part.get_filename():
                content_type = part.get_content_subtype()
                if content_type in ['plain', 'html']:
                    body[content_type] = self._decode_content(part)
    
    def _process_singlepart(self, msg: email.message.EmailMessage, body: EmailBody) -> None:
        """Process single part email content."""
        content_type = msg.get_content_subtype()
        if content_type in ['plain', 'html']:
            body[content_type] = self._decode_content(msg)
    
    def _normalize_body_content(self, body: EmailBody) -> None:
        """Ensure consistent body content format."""
        if not body['plain'] and body['html']:
            body['plain'] = 'This email contains HTML content only.'
        if not body['html'] and body['plain']:
            body['html'] = ''
    
    def _decode_content(self, part: email.message.EmailMessage) -> str:
        """Decode email content with encoding fallback."""
        try:
            return part.get_payload(decode=True).decode()
        except UnicodeDecodeError:
            return part.get_payload(decode=True).decode('latin-1')
    
    def _extract_attachments(self, msg: email.message.EmailMessage) -> List[EmailAttachment]:
        """Extract email attachments."""
        attachments: List[EmailAttachment] = []
        
        try:
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                    
                if filename := part.get_filename():
                    self._process_attachment(part, filename, attachments)
                    
        except Exception as e:
            logger.warning("Attachment extraction failed: %s", e)
            
        return attachments
    
    def _process_attachment(self, part: email.message.EmailMessage, 
                          filename: str, attachments: List[EmailAttachment]) -> None:
        """Process single attachment."""
        try:
            content = part.get_payload(decode=True)
            attachments.append({
                'name': filename,
                'type': part.get_content_type(),
                'size': len(content),
                'content': content
            })
        except Exception as e:
            logger.warning("Failed to process attachment %s: %s", filename, e)
