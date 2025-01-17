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

### Processing Emails

To process a folder of `.eml` files, use the following command:

```bash
python -m src.main /path/to/email/folder
```

#### Options
- `--output` or `-o`: Specify the output directory (default: current directory).
- `--exclude-html`: Exclude HTML content from the processed output.

#### Examples

1. Process emails with default settings:
   ```bash
   python -m src.main ./my_emails
   ```

2. Specify a custom output directory:
   ```bash
   python -m src.main ./my_emails --output ./processed_data
   ```

3. Process emails without HTML content:
   ```bash
   python -m src.main ./my_emails --exclude-html
   ```

---

### Output Structure

After processing, the output directory will be organized as follows:

```
output_directory/
├── data/
│   ├── processed/       # Contains processed email JSON files
│   ├── attachments/     # Contains extracted email attachments
│   └── search_index/    # Contains search index files
```

---

## Search Functionality

### Using the Search Engine

You can search through processed emails using Python code:

```python
from pathlib import Path
from src.scripts.search_engine import SearchEngine

# Initialize search engine
search_engine = SearchEngine(Path('./output_directory'))

# Basic search across all fields (subject, body, sender, recipient)
results = search_engine.search("important meeting")

# Search in specific fields
results = search_engine.search(
    "john@example.com",
    fields=['sender', 'recipient']
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
   - Body (both plain text and HTML)
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

- **Python**: 3.11 or higher.
- **Required Packages**:
  - `whoosh` (for search functionality).

---
