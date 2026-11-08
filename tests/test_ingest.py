import json
import sys

from src.cli import search as search_cli
from src.cli.ingest import process_folder
from src.config.paths import DATA_DIR
from src.core.search_engine import SearchEngine


def test_custom_data_dir_holds_everything(mail_dir, data_dir):
    default_existed = DATA_DIR.exists()
    process_folder(mail_dir, data_dir)

    ids = (data_dir / 'processed' / 'email_ids.txt').read_text().split()
    summary = json.loads((data_dir / 'processed' / 'email_summary.json').read_text())
    assert len(ids) == 2
    assert summary['total_emails'] == 2
    assert len(list((data_dir / 'processed').glob('*.json'))) == 3
    assert list((data_dir / 'attachments').rglob('menu.txt'))
    assert DATA_DIR.exists() == default_existed

    results = SearchEngine(data_dir / 'search_index').search('quarterly')
    assert [r['subject'] for r in results] == ['Quarterly report']


def test_rerun_skips_duplicates(mail_dir, data_dir):
    process_folder(mail_dir, data_dir)
    process_folder(mail_dir, data_dir)
    summary = json.loads((data_dir / 'processed' / 'email_summary.json').read_text())
    assert summary['total_emails'] == 2


def test_search_cli_data_dir(mail_dir, data_dir, monkeypatch, capsys):
    process_folder(mail_dir, data_dir)
    monkeypatch.setattr(sys, 'argv', ['search', 'subject:lunch', '-d', str(data_dir)])
    search_cli.main()
    out = capsys.readouterr().out
    assert 'Found 1 matching emails' in out
    assert 'Subject: Lunch on Friday' in out
