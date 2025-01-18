"""
File handling utilities for InboxForge.
Manages local file operations for attachments and processed data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Union
from src.paths import DATA_DIR

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles local file operations for email data and attachments."""
    
    def __init__(self, data_dir: Union[None, str, Path] = None):
        """
        Initialize the file handler.
        
        Args:
            data_dir: Optional custom data directory path. If None, uses default paths.
            
        Raises:
            FileNotFoundError: If data directory is invalid or inaccessible
        """
        self.data_dir = self._validate_data_dir(data_dir)
        self.attachments_dir = self.data_dir / 'attachments'
        self.processed_dir = self.data_dir / 'processed'
        
        if data_dir:
            logger.warning(f"Using NON-default data directory: {self.data_dir}")
            
        self._ensure_directories()
    
    def _validate_data_dir(self, data_dir: Union[None, str, Path]) -> Path:
        """
        Validate and return the data directory path.
        
        Args:
            data_dir: Data directory path to validate
            
        Returns:
            Path: Validated data directory path
            
        Raises:
            FileNotFoundError: If directory is invalid or inaccessible
        """
        if not data_dir:
            return DATA_DIR
            
        path = Path(data_dir)
        if not path.exists() and path.name == 'data':
            raise FileNotFoundError(f"Invalid data directory: {path}")
            
        return path
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def save_attachment(self, email_id: str, attachment: Dict) -> str:
        """
        Save an email attachment to the attachments directory.
        
        Args:
            email_id: Unique identifier for the email
            attachment: Dictionary containing attachment data and metadata
            
        Returns:
            str: Relative path to the saved attachment
            
        Raises:
            IOError: If attachment cannot be saved
        """
        attachment_dir = self.attachments_dir / email_id
        attachment_dir.mkdir(exist_ok=True)
        
        safe_filename = Path(attachment['name']).name
        file_path = attachment_dir / safe_filename
        
        try:
            with open(file_path, 'wb') as f:
                f.write(attachment['content'])
        except IOError as e:
            logger.error(f"Failed to save attachment {safe_filename}: {e}")
            raise
            
        return str(file_path.relative_to(self.data_dir))
    
    def save_processed_email(self, email_data: Dict) -> None:
        """
        Save processed email data as JSON.
        
        Args:
            email_data: Processed email data dictionary
            
        Raises:
            IOError: If email data cannot be saved
        """
        json_path = self.processed_dir / f"{email_data['id']}.json"
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save email data {email_data['id']}: {e}")
            raise
    
    def get_processed_email(self, email_id: str) -> Dict:
        """
        Retrieve processed email data.
        
        Args:
            email_id: Unique identifier for the email
            
        Returns:
            dict: Email data
            
        Raises:
            FileNotFoundError: If email data file does not exist
            IOError: If email data cannot be read
        """
        json_path = self.processed_dir / f"{email_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Email data not found: {email_id}")
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except IOError as e:
            logger.error(f"Failed to read email data {email_id}: {e}")
            raise