"""
Process email files (.eml) into a searchable format.

Converts emails to JSON and builds a search index for fast retrieval. Features include:
- Recursive email file processing
- Content/metadata extraction
- Search indexing
- Attachment handling
- Optional HTML preservation

Usage:
    python -m src.scripts.ingest emails/                  # Basic usage
    python -m src.scripts.ingest emails/ -d /data/inbox   # Custom data dir
    python -m src.scripts.ingest emails/ --include-html   # Keep HTML
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Set, Tuple, Optional

from src.classes.json_organizer import JsonOrganizer
from src.classes.search_engine import SearchEngine
from src.paths import EMAIL_IDS_FILE
from src.types.emails import ProcessingSummary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

INCLUDE_HTML = False  # Default HTML handling setting


def find_email_files(input_folder: Path) -> List[Path]:
    """Find all .eml files in input folder recursively."""
    if not input_folder.exists():
        logger.error(f'Input folder not found: {input_folder}')
        sys.exit(1)

    logger.info(f'Scanning for emails in: {input_folder}')
    return sorted(input_folder.glob('**/*.eml'))


def validate_email_files(email_files: List[Path], input_folder: Path) -> bool:
    """Check if valid email files exist and provide guidance if not."""
    if email_files:
        return True

    logger.warning('No .eml files found')
    logger.info(
        'Please check that your email files:\n'
        f'1. Use the .eml extension\n'
        f'2. Are located in: {input_folder}\n'
        '3. Are readable by the current user'
    )
    return False


def load_existing_ids() -> Set[str]:
    """Load previously processed email IDs from tracking file."""
    if not EMAIL_IDS_FILE.exists():
        return set()

    with open(EMAIL_IDS_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def save_existing_ids(email_ids: Set[str]) -> None:
    """Save processed email IDs to tracking file."""
    EMAIL_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EMAIL_IDS_FILE, 'w') as f:
        f.writelines(f'{id}\n' for id in sorted(email_ids))


def process_single_email(
    eml_file: Path, json_organizer: JsonOrganizer, search_engine: SearchEngine
) -> Tuple[bool, bool]:
    """
    Process a single email file.

    Returns:
        Tuple of (success, was_skipped) booleans
    """
    try:
        if email_data := json_organizer.process_email(eml_file):
            search_engine.index_email(email_data)
            return True, False
        return False, True
    except Exception as e:
        logger.error(f'Failed to process {eml_file.name}: {str(e)}', exc_info=True)
        return False, False


def log_processing_results(
    processed_count: int,
    skipped_count: int,
    error_count: int,
    summary: ProcessingSummary,
) -> None:
    """Log email processing statistics and output locations."""
    logger.info(
        'Processing complete\n'
        f'Successfully processed: {processed_count} emails\n'
        f'Skipped duplicates: {skipped_count} emails'
    )

    if error_count:
        logger.warning(f'Failed to process: {error_count} emails')

    logger.info(
        f"Total emails in system: {summary['total_emails']}\n"
        f"Last updated: {summary['last_updated']}"
    )


def process_folder(
    input_folder: Path,
    data_dir: Optional[Path] = None,
    include_html: bool = INCLUDE_HTML,
) -> None:
    """
    Process all emails in a folder.

    Finds .eml files, converts to JSON format, builds search index, and tracks progress.
    """
    # Validate input files exist
    if not (email_files := find_email_files(input_folder)) or not validate_email_files(
        email_files, input_folder
    ):
        return

    # Initialize processing
    existing_ids = load_existing_ids()
    total_emails = len(email_files)

    logger.info(
        f"Found {len(existing_ids)} existing emails\n"
        f"Found {total_emails} new emails to process\n"
        f"HTML content will be {'included' if include_html else 'excluded'}"
    )

    if data_dir is not None:
        index_dir = data_dir / 'search_index'
        if not index_dir.exists():
            raise FileNotFoundError(f'Index directory does not exist: {index_dir}')
    else:
        index_dir = None  # default

    # Set up processors
    json_organizer = JsonOrganizer(
        data_dir, exclude_html=not include_html, existing_ids=existing_ids
    )
    search_engine = SearchEngine(index_dir)

    # Process emails
    processed = skipped = errors = 0
    for i, eml_file in enumerate(email_files, 1):
        logger.info(f'Processing {i}/{total_emails}: {eml_file.name}')
        success, was_skipped = process_single_email(eml_file, json_organizer, search_engine)

        if success:
            processed += 1
        elif was_skipped:
            skipped += 1
        else:
            errors += 1

    # Save results
    save_existing_ids(json_organizer.get_email_ids())
    log_processing_results(processed, skipped, errors, json_organizer.get_processing_summary())


def main() -> None:
    """Parse command line arguments and run email processing."""
    parser = argparse.ArgumentParser(
        description='Import email files (.eml) into a searchable format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.scripts.ingest emails/                  # Basic usage
  python -m src.scripts.ingest emails/ -d /data/inbox   # Custom data dir
  python -m src.scripts.ingest emails/ --include-html   # Keep HTML
""",
    )

    parser.add_argument('folder', help='Folder containing .eml files')
    parser.add_argument(
        '--data-dir', '-d', help='Data directory (default: auto-detect)', default=None
    )
    parser.add_argument('--include-html', action='store_true', help='Preserve HTML content')

    args = parser.parse_args()

    try:
        process_folder(
            Path(args.folder),
            Path(args.data_dir) if args.data_dir else None,
            include_html=args.include_html,
        )
    except Exception:
        logger.critical('Fatal error during processing', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
