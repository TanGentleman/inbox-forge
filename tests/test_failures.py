import json
import shutil

from inbox_forge.cli.ingest import process_folder
from inbox_forge.utils.file_handler import FileHandler


def total_emails(data_dir):
    return json.loads((data_dir / 'processed' / 'email_summary.json').read_text())['total_emails']


def test_failed_email_is_retried_on_next_run(mail_dir, tmp_path, data_dir, monkeypatch):
    held = shutil.move(mail_dir / 'lunch.eml', tmp_path / 'lunch.eml')
    process_folder(mail_dir, data_dir)
    shutil.move(held, mail_dir / 'lunch.eml')

    def disk_full(self, email_id, attachment):
        raise OSError('disk full')

    with monkeypatch.context() as m:
        m.setattr(FileHandler, 'save_attachment', disk_full)
        process_folder(mail_dir, data_dir)
    assert total_emails(data_dir) == 1

    process_folder(mail_dir, data_dir)
    assert total_emails(data_dir) == 2
    ids = (data_dir / 'processed' / 'email_ids.txt').read_text().split()
    assert len(ids) == len(set(ids)) == 2


def test_copy_of_failed_email_is_not_skipped(mail_dir, tmp_path, data_dir, monkeypatch):
    held = shutil.move(mail_dir / 'lunch.eml', tmp_path / 'lunch.eml')
    process_folder(mail_dir, data_dir)
    shutil.copy(held, mail_dir / 'lunch-a.eml')
    shutil.copy(held, mail_dir / 'lunch-b.eml')

    save = FileHandler.save_attachment
    calls = []

    def fail_once(self, email_id, attachment):
        calls.append(email_id)
        if len(calls) == 1:
            raise OSError('disk full')
        return save(self, email_id, attachment)

    monkeypatch.setattr(FileHandler, 'save_attachment', fail_once)
    process_folder(mail_dir, data_dir)
    assert total_emails(data_dir) == 2


def test_duplicate_file_in_same_run_is_skipped(mail_dir, data_dir):
    shutil.copy(mail_dir / 'report.eml', mail_dir / 'report-copy.eml')
    process_folder(mail_dir, data_dir)
    assert total_emails(data_dir) == 2
