from inbox_forge.core.email_parser import EmailParser


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


HTML_ONLY = b"""From: Dana <dana@example.org>
To: alice@example.com
Subject: Team offsite
Date: Mon, 02 Sep 2024 09:30:00 +0200
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

<html><head><style>p { color: red; }</style></head>
<body><p>The <b>offsite</b> is in Lisbon this year.</p><script>track()</script></body></html>
"""


def test_html_only_email_gets_plain_text(tmp_path):
    eml = tmp_path / 'invite.eml'
    eml.write_bytes(HTML_ONLY)
    email = EmailParser().parse_email_file(eml)
    assert email['body']['plain'] == 'The offsite is in Lisbon this year.'
    assert '<b>offsite</b>' in email['body']['html']


def test_html_only_email_is_searchable(tmp_path):
    from inbox_forge.cli.ingest import process_folder
    from inbox_forge.core.search_engine import SearchEngine

    (tmp_path / 'mail').mkdir()
    (tmp_path / 'mail' / 'invite.eml').write_bytes(HTML_ONLY)
    process_folder(tmp_path / 'mail', tmp_path / 'inbox')
    results = SearchEngine(tmp_path / 'inbox' / 'search_index').search('lisbon')
    assert [r['subject'] for r in results] == ['Team offsite']


def test_body_uses_declared_charset(tmp_path):
    eml = tmp_path / 'cp1252.eml'
    eml.write_bytes(
        b'From: a@example.com\nSubject: cp1252\n'
        b'Content-Type: text/plain; charset=windows-1252\n'
        b'Content-Transfer-Encoding: 8bit\n\nCaf\xe9 \x96 r\xe9sum\xe9\n'
    )
    assert EmailParser().parse_email_file(eml)['body']['plain'].strip() == 'Café – résumé'


def test_unknown_charset_falls_back_to_latin1(tmp_path):
    eml = tmp_path / 'bogus.eml'
    eml.write_bytes(
        b'From: a@example.com\nSubject: bogus\n'
        b'Content-Type: text/plain; charset=x-not-a-charset\n\nCaf\xe9\n'
    )
    assert EmailParser().parse_email_file(eml)['body']['plain'].strip() == 'Café'
