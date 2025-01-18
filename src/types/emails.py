from typing import TypedDict, List, Optional

class EmailBody(TypedDict):
    """Email body content in plain text and optional HTML."""
    plain: str
    html: Optional[str]

class EmailAttachment(TypedDict):
    """Email attachment metadata and content."""
    name: str
    type: str
    size: int
    content: bytes

# The output of EmailParser
class ParsedEmail(TypedDict):
    """Complete parsed email data structure."""
    id: str
    sender: str
    recipient: List[str]
    subject: str
    date: str
    body: EmailBody
    attachments: List[EmailAttachment]

class EmailMetadata(TypedDict):
    """Schema for email metadata."""
    sender: str
    recipient: List[str]
    subject: str
    date: str
    original_file: str
    processed_date: str


# Created by JSON Organizer
class ProcessedEmail(TypedDict):
    """Schema for processed email data."""
    id: str
    metadata: EmailMetadata
    content: str
    attachments: List[EmailAttachment]

class SummaryEmail(TypedDict):
    """Schema for summary email entry."""
    id: str
    subject: str
    date: str

class ProcessingSummary(TypedDict):
    """Schema for email processing summary."""
    total_emails: int
    last_updated: str
    emails: List[SummaryEmail]
