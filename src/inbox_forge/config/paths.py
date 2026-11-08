from pathlib import Path

# Default data directory, relative to where the command runs
DATA_DIR = Path('data')

# Data subdirectories
ATTACHMENTS_DIR = DATA_DIR / 'attachments'
PROCESSED_DIR = DATA_DIR / 'processed'
SEARCH_INDEX_DIR = DATA_DIR / 'search_index'

# Summary file path
SUMMARY_FILE = PROCESSED_DIR / 'email_summary.json'

# Email IDs tracking file
EMAIL_IDS_FILE = PROCESSED_DIR / 'email_ids.txt'
