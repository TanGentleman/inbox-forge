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
    
    def generate_email_id(self, email_content: bytes) -> str:
        """
        Generate a unique ID for the email using its content.
        
        Args:
            email_content: Raw email content bytes
            
        Returns:
            str: 16-character hexadecimal ID
        """
        return hashlib.sha256(email_content).hexdigest()[:16]
    
    def parse_email_file(self, eml_path: Union[str, Path]) -> ParsedEmail:
        """
        Parse an .eml file and extract relevant information.
        
        Args:
            eml_path: Path to the .eml file
            
        Returns:
            ParsedEmail: Dictionary containing parsed email data with fields:
                id, sender, recipient, subject, date, body, attachments
                
        Raises:
            IOError: If file cannot be read
            email.errors.MessageParseError: If email parsing fails
        """
        try:
            with open(eml_path, 'rb') as f:
                content = f.read()
                email_msg = self.parser.parsebytes(content)
            
            email_data: ParsedEmail = {
                'id': self.generate_email_id(content),
                'sender': self._extract_sender(email_msg),
                'recipient': self._extract_recipients(email_msg),
                'subject': self._extract_subject(email_msg),
                'date': self._parse_date(email_msg.get('date')),
                'body': self._extract_body(email_msg),
                'attachments': self._extract_attachments(email_msg)
            }
            
            logger.debug("Extracted email data - Subject: %s, Sender: %s, Date: %s", 
                        email_data['subject'], email_data['sender'], email_data['date'])
            
            return email_data
            
        except Exception as e:
            logger.error("Error parsing %s: %s", eml_path, str(e))
            raise
    
    def _extract_subject(self, email_msg: email.message.EmailMessage) -> str:
        """
        Extract and clean the email subject.
        
        Args:
            email_msg: Parsed email message
            
        Returns:
            str: Email subject or '[No Subject]' if not found
        """
        try:
            subject = email_msg.get('subject', '')
            return subject if subject is not None else '[No Subject]'
        except Exception as e:
            logger.warning("Could not extract subject: %s", e)
            return '[No Subject]'
    
    def _extract_sender(self, email_msg: email.message.EmailMessage) -> str:
        """
        Extract and normalize the sender's email address.
        
        Args:
            email_msg: Parsed email message
            
        Returns:
            str: Sender email address or '[No Sender]' if not found
        """
        try:
            return email_msg.get('from', '[No Sender]')
        except Exception as e:
            logger.warning("Could not extract sender: %s", e)
            return '[No Sender]'
    
    def _extract_recipients(self, email_msg: email.message.EmailMessage) -> List[str]:
        """
        Extract all recipients (To, CC, BCC).
        
        Args:
            email_msg: Parsed email message
            
        Returns:
            List[str]: List of recipient email addresses
        """
        recipients = []
        try:
            for header in ['to', 'cc', 'bcc']:
                if header_val := email_msg.get(header):
                    recipients.extend(addr.strip() for addr in header_val.split(','))
            return recipients if recipients else ['[No Recipients]']
        except Exception as e:
            logger.warning("Could not extract recipients: %s", e)
            return ['[No Recipients]']
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """
        Parse email date into ISO format.
        
        Args:
            date_str: Raw date string from email
            
        Returns:
            str: ISO formatted date string
        """
        try:
            if not date_str:
                return datetime.now().isoformat()
            
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date.isoformat()
        except Exception as e:
            logger.warning("Could not parse date: %s", e)
            return datetime.now().isoformat()
    
    def _extract_body(self, email_msg: email.message.EmailMessage) -> EmailBody:
        """
        Extract both plain text and HTML body content.
        
        Args:
            email_msg: Parsed email message
            
        Returns:
            EmailBody: Dictionary with 'plain' and 'html' content
        """
        body: EmailBody = {'plain': '', 'html': ''}
        
        try:
            if email_msg.is_multipart():
                self._handle_multipart_body(email_msg, body)
            else:
                self._handle_single_part_body(email_msg, body)
                
            # Ensure consistent body content
            if not body['plain'] and body['html']:
                body['plain'] = 'This email contains HTML content only.'
            if not body['html'] and body['plain']:
                body['html'] = ''
                
        except Exception as e:
            logger.warning("Could not extract body: %s", e)
            body['plain'] = '[Could not extract email body]'
            body['html'] = ''
            
        return body
    
    def _handle_multipart_body(self, email_msg: email.message.EmailMessage, body: EmailBody) -> None:
        """Helper method to handle multipart email bodies."""
        for part in email_msg.walk():
            if part.get_content_maintype() == 'text' and not part.get_filename():
                content_type = part.get_content_subtype()
                if content_type in ['plain', 'html']:
                    body[content_type] = self._decode_content(part)
    
    def _handle_single_part_body(self, email_msg: email.message.EmailMessage, body: EmailBody) -> None:
        """Helper method to handle single part email bodies."""
        content_type = email_msg.get_content_subtype()
        if content_type in ['plain', 'html']:
            body[content_type] = self._decode_content(email_msg)
    
    def _decode_content(self, part: email.message.EmailMessage) -> str:
        """Helper method to decode email content with fallback encoding."""
        try:
            return part.get_payload(decode=True).decode()
        except UnicodeDecodeError:
            return part.get_payload(decode=True).decode('latin-1')
    
    def _extract_attachments(self, email_msg: email.message.EmailMessage) -> List[EmailAttachment]:
        """
        Extract attachment metadata from email.
        
        Args:
            email_msg: Parsed email message
            
        Returns:
            List[EmailAttachment]: List of attachment metadata dictionaries
        """
        attachments: List[EmailAttachment] = []
        try:
            for part in email_msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                    
                if filename := part.get_filename():
                    try:
                        content = part.get_payload(decode=True)
                        attachments.append({
                            'name': filename,
                            'type': part.get_content_type(),
                            'size': len(content),
                            'content': content
                        })
                    except Exception as e:
                        logger.warning("Could not process attachment %s: %s", filename, e)
        except Exception as e:
            logger.warning("Could not extract attachments: %s", e)
            
        return attachments
