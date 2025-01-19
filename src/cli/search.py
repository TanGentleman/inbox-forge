"""
Command-line interface for searching InboxForge emails.

Usage:
    # Basic search
    python -m src.scripts.search "important meeting"

    # Search by field
    python -m src.scripts.search "from:john@example.com"
    python -m src.scripts.search "project report" --in subject,content

    # Filter by date
    python -m src.scripts.search "meeting" --after 2024-01-01 --before 2024-03-01

Supports:
    - Field prefixes: from:, to:, subject:
    - Field filtering: --in subject,content,sender,recipient
    - Date filtering: --after/--before YYYY-MM-DD
    - Custom index location: --dir PATH
"""

from pathlib import Path
import argparse
from datetime import datetime
from typing import Optional
from core.search_engine import SearchEngine
from src.paths import SEARCH_INDEX_DIR
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD date string."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None


def format_result(result: dict) -> str:
    """Format search result for display."""
    date = result['date'].strftime('%Y-%m-%d %H:%M')
    return (
        f"\nDate: {date}\n"
        f"From: {result['sender']}\n"
        f"To: {result['recipient']}\n"
        f"Subject: {result['subject']}\n"
        f"ID: {result['id']}"
    )


def verify_index_location(index_dir: Path) -> bool:
    """Verify InboxForge directory structure exists."""
    if index_dir != SEARCH_INDEX_DIR:
        logger.error(f'Error: Index directory must be {SEARCH_INDEX_DIR}')
        return False
    return True


def parse_query(query: str) -> tuple[str, list]:
    """Parse query string for field prefixes (from:, to:, subject:)."""
    fields = []

    if query.startswith('from:'):
        fields = ['sender']
        query = query.replace('from:', '')
    elif query.startswith('to:'):
        fields = ['recipient']
        query = query.replace('to:', '')
    elif query.startswith('subject:'):
        fields = ['subject']
        query = query.replace('subject:', '')

    return query.strip(), fields


def main():
    parser = argparse.ArgumentParser(
        description='Search through InboxForge emails.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.scripts.search "important meeting"              # Search all fields
  python -m src.scripts.search "from:john@example.com"         # Search by sender
  python -m src.scripts.search "meeting" --in subject,content     # Search specific fields
  python -m src.scripts.search "report" --after 2024-01-01     # Filter by date
""",
    )

    parser.add_argument(
        'query', help='Search query (e.g. "important meeting", "from:john@example.com")'
    )
    parser.add_argument(
        '--in',
        dest='fields',
        help='Fields to search: subject,content,sender,recipient',
        type=lambda s: [x.strip() for x in s.split(',')],
    )
    parser.add_argument('--after', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--before', help='End date (YYYY-MM-DD)')
    parser.add_argument('--dir', '-d', help='Index directory (default: auto-detect)')

    args = parser.parse_args()
    index_dir = Path(args.dir) if args.dir else None

    if index_dir and not verify_index_location(index_dir):
        return

    search_engine = SearchEngine(index_dir)
    query, detected_fields = parse_query(args.query)
    fields = args.fields if args.fields else detected_fields

    date_range = None
    if args.after or args.before:
        start_date = parse_date(args.after) if args.after else None
        end_date = parse_date(args.before) if args.before else None
        if (args.after and not start_date) or (args.before and not end_date):
            print('\nError: Invalid date format. Use YYYY-MM-DD')
            print('Example: --after 2024-01-01 --before 2024-12-31')
            return
        date_range = (start_date, end_date)

    try:
        results = search_engine.search(query=query, fields=fields, date_range=date_range)
    except ValueError as e:
        print(f'\nError: {str(e)}')
        return

    if not results:
        print('\nNo matching emails found.')
        print('Tips: Check spelling, use fewer words, try different date range')
        return

    print(f'\nFound {len(results)} matching emails:')
    for result in results:
        print(format_result(result))


if __name__ == '__main__':
    main()
