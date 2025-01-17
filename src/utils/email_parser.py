"""
Email parser utility for InboxForge.
Handles parsing of .eml files into structured data.
"""

import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import hashlib

class EmailParser:
    """Parses .eml files and extracts structured data."""
    
    def __init__(self):
        self.parser = BytesParser(policy=policy.default)
    
    def generate_email_id(self, email_content: bytes) -> str:
        """Generate a unique ID for the email using its content."""
        return hashlib.sha256(email_content).hexdigest()[:16]
    
    def parse_email_file(self, eml_path: Union[str, Path]) -> Dict:
        """Parse an .eml file and extract relevant information."""
        try:
            with open(eml_path, 'rb') as f:
                content = f.read()
                email_msg = self.parser.parsebytes(content)
            
            # Extract body content
            body = self._extract_body(email_msg)
            
            # Extract all fields with proper error handling
            email_data = {
                'id': self.generate_email_id(content),
                'sender': self._extract_sender(email_msg),
                'recipient': self._extract_recipients(email_msg),
                'subject': self._extract_subject(email_msg),
                'date': self._parse_date(email_msg.get('date')),
                'body': body,
                'attachments': self._extract_attachments(email_msg)
            }
            
            # Debug print
            print(f"\nDebug - Extracted email data:")
            print(f"Subject: {email_data['subject']}")
            print(f"Sender: {email_data['sender']}")
            print(f"Date: {email_data['date']}")
            
            return email_data
            
        except Exception as e:
            print(f"\nError details while parsing {eml_path}:")
            print(f"Exception: {str(e)}")
            raise
    
    def _extract_subject(self, email_msg: email.message.EmailMessage) -> str:
        """Extract and clean the email subject."""
        try:
            subject = email_msg.get('subject', '')
            return subject if subject is not None else '[No Subject]'
        except Exception as e:
            print(f"Warning: Could not extract subject: {e}")
            return '[No Subject]'
    
    def _extract_sender(self, email_msg: email.message.EmailMessage) -> str:
        """Extract and normalize the sender's email address."""
        try:
            return email_msg.get('from', '[No Sender]')
        except Exception as e:
            print(f"Warning: Could not extract sender: {e}")
            return '[No Sender]'
    
    def _extract_recipients(self, email_msg: email.message.EmailMessage) -> List[str]:
        """Extract all recipients (To, CC, BCC)."""
        recipients = []
        try:
            for header in ['to', 'cc', 'bcc']:
                if email_msg.get(header):
                    recipients.extend([addr.strip() for addr in 
                                    email_msg.get(header, '').split(',')])
            return recipients if recipients else ['[No Recipients]']
        except Exception as e:
            print(f"Warning: Could not extract recipients: {e}")
            return ['[No Recipients]']
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse email date into ISO format."""
        try:
            if not date_str:
                return datetime.now().isoformat()
            
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date.isoformat()
        except Exception as e:
            print(f"Warning: Could not parse date: {e}")
            return datetime.now().isoformat()
    
    def _extract_body(self, email_msg: email.message.EmailMessage) -> Dict[str, str]:
        """Extract both plain text and HTML body content."""
        body = {'plain': '', 'html': ''}
        
        try:
            if email_msg.is_multipart():
                # Handle multipart messages
                for part in email_msg.walk():
                    if part.get_content_maintype() == 'text' and not part.get_filename():
                        content_type = part.get_content_subtype()
                        if content_type in ['plain', 'html']:
                            try:
                                body[content_type] = part.get_payload(decode=True).decode()
                            except UnicodeDecodeError:
                                body[content_type] = part.get_payload(decode=True).decode('latin-1')
            else:
                # Handle non-multipart messages
                content_type = email_msg.get_content_subtype()
                if content_type in ['plain', 'html']:
                    try:
                        body[content_type] = email_msg.get_payload(decode=True).decode()
                    except UnicodeDecodeError:
                        body[content_type] = email_msg.get_payload(decode=True).decode('latin-1')
                
            # If we have no plain text but have HTML, create a simple plain text version
            if not body['plain'] and body['html']:
                body['plain'] = 'This email contains HTML content only.'
                
            # If we have no HTML but have plain text, set HTML to empty
            if not body['html'] and body['plain']:
                body['html'] = ''
                
        except Exception as e:
            print(f"Warning: Could not extract body properly: {e}")
            body['plain'] = '[Could not extract email body]'
            body['html'] = ''
            
        return body
    
    def _extract_attachments(self, email_msg: email.message.EmailMessage) -> List[Dict]:
        """Extract attachment metadata from email."""
        attachments = []
        try:
            for part in email_msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                    
                filename = part.get_filename()
                if filename:
                    try:
                        attachments.append({
                            'name': filename,
                            'type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)),
                            'content': part.get_payload(decode=True)
                        })
                    except Exception as e:
                        print(f"Warning: Could not process attachment {filename}: {e}")
        except Exception as e:
            print(f"Warning: Could not extract attachments: {e}")
            
        return attachments 
