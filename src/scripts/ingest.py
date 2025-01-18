"""
Command-line interface for ingesting emails into InboxForge.

This script processes email files (.eml) from a specified directory, converting them
into a searchable JSON format and building a search index. It handles both plain text
and HTML content, with options to include HTML if desired.

Usage:
    # Basic ingestion (HTML excluded by default)
    python -m src.scripts.ingest /path/to/email/folder
    
    # Specify output directory
    python -m src.scripts.ingest /path/to/email/folder --output /path/to/output
    
    # Include HTML content
    python -m src.scripts.ingest /path/to/email/folder --include-html
"""

from pathlib import Path
import argparse
import sys
import logging
from typing import Optional
from src.paths import EMAIL_IDS_FILE
from src.classes.json_organizer import JsonOrganizer
from src.classes.search_engine import SearchEngine

# Default configuration
INCLUDE_HTML = False

# Configure logging with timestamp and log level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def find_email_files(input_folder: Path) -> list[Path]:
    """
    Recursively find all .eml files in the input folder.
    
    Args:
        input_folder: Directory to search for email files
        
    Returns:
        List of paths to .eml files
        
    Raises:
        SystemExit: If input folder does not exist
    """
    if not input_folder.exists():
        logger.error(f"Input folder does not exist: {input_folder}")
        sys.exit(1)
        
    logger.info(f"Scanning directory: {input_folder}")
    return list(input_folder.glob('**/*.eml'))

def validate_email_files(email_files: list[Path], input_folder: Path) -> Optional[bool]:
    """
    Validate that email files were found and provide helpful messages if not.
    
    Args:
        email_files: List of found .eml file paths
        input_folder: Directory that was searched
        
    Returns:
        True if files were found, None if no files found
    """
    if not email_files:
        logger.warning("No .eml files found in the specified directory")
        logger.info("Please ensure your email files:")
        logger.info("1. End with the .eml extension")
        logger.info("2. Are located in: %s", input_folder)
        logger.info("3. Have appropriate read permissions")
        return None
    return True

def load_existing_ids(base_dir: Path) -> set[str]:
    """
    Load existing email IDs from storage.
    
    Args:
        base_dir: Base directory for data storage
        
    Returns:
        Set of existing email IDs
    """
    if not EMAIL_IDS_FILE.exists():
        return set()
        
    with open(EMAIL_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_existing_ids(base_dir: Path, email_ids: set[str]) -> None:
    """
    Save email IDs to storage.
    
    Args:
        base_dir: Base directory for data storage
        email_ids: Set of email IDs to save
    """
    EMAIL_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(EMAIL_IDS_FILE, 'w') as f:
        for email_id in sorted(email_ids):
            f.write(f"{email_id}\n")

def process_folder(input_folder: Path, base_dir: Path, include_html: bool = INCLUDE_HTML) -> None:
    """
    Process and index all emails in the specified directory.
    
    Handles the complete email ingestion workflow:
    1. Finds all .eml files recursively
    2. Processes each email into JSON format
    3. Indexes the emails for searching
    4. Provides progress updates and summary
    
    Args:
        input_folder: Directory containing .eml files
        base_dir: Base output directory for processed files
        include_html: Whether to include HTML content in processing
    """
    email_files = find_email_files(input_folder)
    if not validate_email_files(email_files, input_folder):
        return
        
    # Load existing IDs
    existing_ids = load_existing_ids(base_dir)
    logger.info(f"Loaded {len(existing_ids)} existing email IDs")
    
    total_emails = len(email_files)
    logger.info(f"Found {total_emails} email files to process")
    logger.info(f"HTML content will be {'included' if include_html else 'excluded'}")
    
    # Initialize processors with existing IDs
    json_organizer = JsonOrganizer(base_dir, exclude_html=not include_html, existing_ids=existing_ids)
    search_engine = SearchEngine(base_dir)
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each email file
    for i, eml_file in enumerate(email_files, 1):
        try:
            logger.info(f"Processing email {i}/{total_emails}: {eml_file.name}")
            email_data = json_organizer.process_email(eml_file)
            if email_data is None:
                skipped_count += 1
                continue
            search_engine.index_email(email_data)
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to process {eml_file.name}: {str(e)}", exc_info=True)
            error_count += 1
    
    # Save updated IDs
    save_existing_ids(base_dir, json_organizer.get_email_ids())
    
    # Output summary
    logger.info("Processing complete")
    logger.info(f"Successfully processed: {processed_count} emails")
    logger.info(f"Skipped duplicates: {skipped_count} emails")
    if error_count:
        logger.warning(f"Failed to process: {error_count} emails")
    
    # Output locations
    logger.info(f"Processed emails location: {base_dir / 'data' / 'processed'}")
    logger.info(f"Attachments location: {base_dir / 'data' / 'attachments'}")
    
    # Processing summary
    summary = json_organizer.get_processing_summary()
    logger.info(f"Total emails in system: {summary['total_emails']}")
    logger.info(f"Last updated: {summary['last_updated']}")

def main() -> None:
    """
    Main entry point for the email ingestion script.
    
    Parses command line arguments and initiates the email processing workflow.
    Provides a clean interface for both basic and advanced usage patterns.
    """
    parser = argparse.ArgumentParser(
        description='Process email files (.eml) into searchable JSON format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python -m src.scripts.ingest /path/to/email/folder
  python -m src.scripts.ingest /path/to/email/folder --output /path/to/output
  python -m src.scripts.ingest /path/to/email/folder --include-html
""")
    
    parser.add_argument('folder', 
                       help='Path to the folder containing .eml files')
    parser.add_argument('--output', '-o', 
                       help='Base directory for output (default: current directory)',
                       default='.')
    parser.add_argument('--include-html',
                       action='store_true',
                       help='Include HTML content in the processed output')
    
    args = parser.parse_args()
    
    try:
        process_folder(
            Path(args.folder),
            Path(args.output),
            include_html=args.include_html
        )
    except Exception as e:
        logger.critical("Fatal error during processing", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()