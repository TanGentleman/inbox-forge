"""
Main entry point for InboxForge.
Processes a folder of emails into organized JSON files with attachment references.
"""

from pathlib import Path
from typing import Optional, List, Dict
import argparse
import sys
from scripts.json_organizer import JsonOrganizer
from scripts.search_engine import SearchEngine

class InboxForge:
    """Main application class for InboxForge."""
    
    def __init__(self, base_dir: Path, exclude_html: bool = False):
        self.base_dir = Path(base_dir)
        self.exclude_html = exclude_html
        self.json_organizer = JsonOrganizer(self.base_dir, exclude_html=exclude_html)
        self.search_engine = SearchEngine(self.base_dir)
    
    def process_folder(self, input_folder: Path) -> None:
        """
        Process all emails in the specified directory.
        
        Args:
            input_folder: Directory containing .eml files
        """
        input_path = Path(input_folder)
        if not input_path.exists():
            print(f"Error: Folder '{input_folder}' does not exist.")
            sys.exit(1)
            
        print(f"\nScanning directory: {input_path}")
        print("Looking for .eml files...")
            
        # Count total emails for progress reporting
        email_files = list(input_path.glob('**/*.eml'))
        total_emails = len(email_files)
        
        if total_emails == 0:
            print("\nNo .eml files found!")
            print("Make sure your email files:")
            print("1. End with the .eml extension")
            print("2. Are in the directory you specified")
            print(f"\nChecked directory: {input_path}")
            print("Supported file types: .eml (email files)")
            return
        
        print(f"\nFound {total_emails} email files to process...")
        print(f"HTML content will be {'excluded' if self.exclude_html else 'included'}")
        
        for i, eml_file in enumerate(email_files, 1):
            try:
                print(f"Processing email {i}/{total_emails}: {eml_file.name}")
                email_data = self.json_organizer.process_email(eml_file)
                self.search_engine.index_email(email_data)
            except Exception as e:
                print(f"Error processing {eml_file.name}: {str(e)}")
        
        print("\nProcessing complete!")
        print(f"Processed emails can be found in: {self.base_dir / 'data' / 'processed'}")
        print(f"Attachments are stored in: {self.base_dir / 'data' / 'attachments'}")
        
        # Show summary of processed emails
        summary = self.json_organizer.get_processing_summary()
        print(f"\nTotal emails processed: {summary['total_emails']}")
        print(f"Last updated: {summary['last_updated']}")

def main():
    parser = argparse.ArgumentParser(
        description='Process a folder of .eml files into organized JSON files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python -m src.main /path/to/email/folder
  python -m src.main /path/to/email/folder --output /path/to/output
  python -m src.main /path/to/email/folder --exclude-html

Note: This program processes .eml files, which are standard email files.
      You can usually export emails from your email client in this format.
""")
    
    parser.add_argument('folder', 
                       help='Path to the folder containing .eml files')
    parser.add_argument('--output', '-o', 
                       help='Base directory for output (default: current directory)',
                       default='.')
    parser.add_argument('--exclude-html',
                       action='store_true',
                       help='Exclude HTML content from the processed output')
    
    args = parser.parse_args()
    
    # Initialize InboxForge with the output directory and HTML preference
    base_dir = Path(args.output)
    inbox_forge = InboxForge(base_dir, exclude_html=args.exclude_html)
    
    # Process the specified folder
    inbox_forge.process_folder(args.folder)

if __name__ == '__main__':
    main() 