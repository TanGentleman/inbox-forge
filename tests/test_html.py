import json

from inbox_forge.cli.ingest import process_folder


def load_processed(data_dir):
    files = (data_dir / 'processed').glob('*.json')
    emails = [json.loads(f.read_text()) for f in files if f.name != 'email_summary.json']
    return {e['metadata']['subject']: e for e in emails}


def test_include_html_handles_plain_only_email(mail_dir, data_dir):
    process_folder(mail_dir, data_dir, include_html=True)
    emails = load_processed(data_dir)
    assert set(emails) == {'Quarterly report', 'Lunch on Friday'}
    assert '<b>lunch</b>' in emails['Lunch on Friday']['content']
    assert '<' not in emails['Quarterly report']['content']


def test_html_excluded_by_default(mail_dir, data_dir):
    process_folder(mail_dir, data_dir)
    assert '<b>' not in load_processed(data_dir)['Lunch on Friday']['content']
