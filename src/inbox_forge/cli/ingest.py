"""
Process email files (.eml) into a searchable format.

Converts emails to JSON and builds a search index for fast retrieval. Features include:
- Recursive email file processing
- Content/metadata extraction
- Search indexing
- Attachment handling
- Optional HTML preservation

Usage:
    inbox-forge ingest emails/                  # Basic usage
    inbox-forge ingest emails/ -d /data/inbox   # Custom data dir
    inbox-forge ingest emails/ --include-html   # Keep HTML
"""

import argparse
import logging
import sys
from pathlib import Path

from inbox_forge.core.json_organizer import JsonOrganizer
from inbox_forge.core.search_engine import SearchEngine
from inbox_forge.types.emails import ProcessingSummary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def find_email_files(input_folder: Path) -> list[Path]:
    """Find all .eml files in input folder recursively."""
    if not input_folder.exists():
        logger.error(f'Input folder not found: {input_folder}')
        sys.exit(1)

    logger.info(f'Scanning for emails in: {input_folder}')
    return sorted(input_folder.glob('**/*.eml'))


def validate_email_files(email_files: list[Path], input_folder: Path) -> bool:
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


def process_single_email(
    eml_file: Path, json_organizer: JsonOrganizer, search_engine: SearchEngine
) -> tuple[bool, bool]:
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
        f'Total emails in system: {summary["total_emails"]}\n'
        f'Last updated: {summary["last_updated"]}'
    )


def process_folder(
    input_folder: Path,
    data_dir: Path | None = None,
    include_html: bool = False,
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

    # Set up processors
    json_organizer = JsonOrganizer(data_dir, exclude_html=not include_html)
    search_engine = SearchEngine(data_dir / 'search_index' if data_dir else None)
    total_emails = len(email_files)

    logger.info(
        f'Found {len(json_organizer.get_email_ids())} existing emails\n'
        f'Found {total_emails} new emails to process\n'
        f'HTML content will be {"included" if include_html else "excluded"}'
    )

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

    log_processing_results(processed, skipped, errors, json_organizer.get_processing_summary())


def main(argv: list[str] | None = None) -> None:
    """Parse command line arguments and run email processing."""
    parser = argparse.ArgumentParser(
        prog='inbox-forge ingest',
        description='Import email files (.eml) into a searchable format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  inbox-forge ingest emails/                  # Basic usage
  inbox-forge ingest emails/ -d /data/inbox   # Custom data dir
  inbox-forge ingest emails/ --include-html   # Keep HTML
""",
    )

    parser.add_argument('folder', help='Folder containing .eml files')
    parser.add_argument(
        '--data-dir', '-d', help='Data directory (default: auto-detect)', default=None
    )
    parser.add_argument('--include-html', action='store_true', help='Preserve HTML content')

    args = parser.parse_args(argv)

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
