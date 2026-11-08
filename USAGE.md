---

# InboxForge Usage Guide

InboxForge is a powerful tool for processing `.eml` files into an organized JSON format with advanced search capabilities. This guide will walk you through its usage and features.

---

## Table of Contents
1. [Basic Usage](#basic-usage)
   - [Processing Emails](#processing-emails)
   - [Output Structure](#output-structure)
2. [Search Functionality](#search-functionality)
   - [Using the Search Engine](#using-the-search-engine)
   - [Search Results](#search-results)
   - [Search Tips](#search-tips)
3. [Processing Details](#processing-details)
4. [Error Handling](#error-handling)
5. [Requirements](#requirements)

---

## Basic Usage

### Installing

```bash
pip install git+https://github.com/TanGentleman/inbox-forge
```

### Processing Emails

To process a folder of `.eml` files, use the following command:

```bash
inbox-forge ingest /path/to/email/folder
```

#### Options
- `--data-dir` or `-d`: Data directory for the index and processed files (default: `data/` in the current directory).
- `--include-html`: Keep HTML content in the processed output (excluded by default).

#### Examples

1. Process emails with default settings:
   ```bash
   inbox-forge ingest ./my_emails
   ```

2. Specify a custom data directory:
   ```bash
   inbox-forge ingest ./my_emails --data-dir ./processed_data
   ```

3. Keep HTML content:
   ```bash
   inbox-forge ingest ./my_emails --include-html
   ```

---

### Output Structure

After processing, the data directory is organized as follows:

```
data/
├── processed/       # Processed email JSON, email_ids.txt, email_summary.json
├── attachments/     # Extracted email attachments
└── search_index/    # Search index files
```

---

## Search Functionality

### Using the Search Engine

From the command line:

```bash
inbox-forge search "important meeting"
inbox-forge search "from:john@example.com"
inbox-forge search "report" --in subject,content --after 2024-01-01
inbox-forge search "report" --data-dir ./processed_data
```

Or from Python:

```python
from pathlib import Path
from inbox_forge.core.search_engine import SearchEngine

# Initialize search engine
search_engine = SearchEngine(Path('data/search_index'))

# Basic search across all fields (subject, content, sender, recipient)
results = search_engine.search("important meeting")

# Search in specific fields
results = search_engine.search(
    "john@example.com",
    fields=['sender', 'recipient'],
)

# Search with a date range
from datetime import datetime
results = search_engine.search(
    "quarterly report",
    date_range=(
        datetime(2023, 1, 1),
        datetime(2023, 12, 31)
    )
)
```

### Search Results

Search results are returned as a list of dictionaries containing:
- `id`: Unique email identifier
- `sender`: Email sender
- `recipient`: Email recipient(s)
- `subject`: Email subject
- `date`: Email date

---

### Search Tips

1. **Indexed Fields**: The search engine indexes the following fields:
   - Subject
   - Content (plain text, plus HTML with `--include-html`)
   - Sender
   - Recipient

2. **Advanced Search**:
   - Use `AND`, `OR`, `NOT` for boolean operations.
   - Use quotes for exact phrases: `"exact phrase"`.
   - Use wildcards: `meet*` matches "meeting", "meets", etc.

---

## Processing Details

- **Supported Formats**: `.eml` (standard email export format).
- **Attachments**: Automatically extracted and saved.
- **Search Index**: Creates a searchable index of email content.
- **Summary**: Maintains a summary of processed emails.
- **Content Handling**: Supports both plain text and HTML email content.

---

## Error Handling

If you encounter errors, follow these steps:

1. Ensure input files are valid `.eml` files.
2. Check write permissions for the output directory.
3. Verify file paths are correct.
4. Review console output for specific error messages.

---

## Requirements

- **Python**: 3.10 or higher.
- **Required Packages** (installed automatically):
  - `whoosh` (for search functionality).

---
