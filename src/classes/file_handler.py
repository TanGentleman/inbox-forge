"""
File handling utilities for InboxForge.
Manages local file operations for attachments and processed data.
"""

import json
from pathlib import Path
from typing import Dict, Union, BinaryIO
import shutil
from src.paths import ATTACHMENTS_DIR, PROCESSED_DIR

class FileHandler:
    """Handles local file operations for email data and attachments."""
    
    def __init__(self, base_dir: Union[str, Path]):
        self.base_dir = Path(base_dir)
        self.attachments_dir = ATTACHMENTS_DIR
        self.processed_dir = PROCESSED_DIR
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def save_attachment(self, email_id: str, attachment: Dict) -> str:
        """
        Save an email attachment to the attachments directory.
        
        Args:
            email_id: Unique identifier for the email
            attachment: Dictionary containing attachment data
            
        Returns:
            str: Path to the saved attachment
        """
        # Create email-specific attachment directory
        attachment_dir = self.attachments_dir / email_id
        attachment_dir.mkdir(exist_ok=True)
        
        # Create safe filename
        safe_filename = Path(attachment['name']).name
        file_path = attachment_dir / safe_filename
        
        # Save attachment content
        with open(file_path, 'wb') as f:
            f.write(attachment['content'])
        
        return str(file_path.relative_to(self.base_dir))
    
    def save_processed_email(self, email_data: Dict) -> None:
        """
        Save processed email data as JSON.
        
        Args:
            email_data: Processed email data dictionary
        """
        json_path = self.processed_dir / f"{email_data['id']}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)
    
    def get_processed_email(self, email_id: str) -> Dict:
        """
        Retrieve processed email data.
        
        Args:
            email_id: Unique identifier for the email
            
        Returns:
            dict: Email data
        """
        json_path = self.processed_dir / f"{email_id}.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f) 