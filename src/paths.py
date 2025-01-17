from pathlib import Path

# Core directory paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'

# Data subdirectories
ATTACHMENTS_DIR = DATA_DIR / 'attachments'
PROCESSED_DIR = DATA_DIR / 'processed'
SEARCH_INDEX_DIR = DATA_DIR / 'search_index'

# Summary file path
SUMMARY_FILE = PROCESSED_DIR / 'email_summary.json'
