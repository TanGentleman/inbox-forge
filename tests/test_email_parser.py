from src.core.email_parser import EmailParser


def test_parses_plain_email(mail_dir):
    email = EmailParser().parse_email_file(mail_dir / 'report.eml')
    assert email['sender'] == 'Alice Smith <alice@example.com>'
    assert email['recipient'] == [
        '"Doe, John" <john@example.com>',
        'bob@example.com',
        'Carol <carol@example.com>',
    ]
    assert email['subject'] == 'Quarterly report'
    assert email['date'] == '2024-03-05T10:00:00-08:00'
    assert 'quarterly report is ready' in email['body']['plain']
    assert email['body']['html'] is None
    assert email['attachments'] == []


def test_parses_multipart_email(mail_dir):
    email = EmailParser().parse_email_file(mail_dir / 'lunch.eml')
    assert email['body']['plain'].startswith('Want to grab lunch')
    assert '<b>lunch</b>' in email['body']['html']
    [attachment] = email['attachments']
    assert attachment['name'] == 'menu.txt'
    assert attachment['content'].strip() == b'Tacos'


def test_missing_headers_get_defaults(tmp_path):
    eml = tmp_path / 'bare.eml'
    eml.write_bytes(b'\n\nno headers here\n')
    email = EmailParser().parse_email_file(eml)
    assert email['subject'] == '[No Subject]'
    assert email['sender'] == '[No Sender]'
    assert email['recipient'] == ['[No Recipients]']
