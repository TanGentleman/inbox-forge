from datetime import datetime

import pytest

from inbox_forge.cli.ingest import process_folder
from inbox_forge.cli.search import parse_query
from inbox_forge.core.search_engine import SearchEngine


@pytest.fixture
def engine(mail_dir, data_dir):
    process_folder(mail_dir, data_dir)
    return SearchEngine(data_dir / 'search_index')


def subjects(results):
    return sorted(r['subject'] for r in results)


REPORT, LUNCH = 'Quarterly report', 'Lunch on Friday'


@pytest.mark.parametrize(
    'query,fields,expected',
    [
        ('quarterly', None, [REPORT]),
        ('LUNCH friday', None, [LUNCH]),
        ('lunch quarterly', None, []),
        ('lunch OR quarterly', None, [LUNCH, REPORT]),
        ('alice NOT lunch', None, [REPORT]),
        ('"grab lunch"', None, [LUNCH]),
        ('"lunch grab"', None, []),
        ('quart*', None, [REPORT]),
        ('', None, [LUNCH, REPORT]),
        ('alice@example.com', ['sender'], [REPORT]),
        ('alice@example.com', ['recipient'], [LUNCH]),
        ('"Doe, John"', ['recipient'], [REPORT]),
        ('carol', ['recipient'], [REPORT]),
        ('review', ['subject'], []),
        ('review', ['content'], [REPORT]),
    ],
)
def test_query(engine, query, fields, expected):
    assert subjects(engine.search(query, fields=fields)) == expected


@pytest.mark.parametrize(
    'date_range,expected',
    [
        ((datetime(2024, 6, 1), None), [LUNCH]),
        ((None, datetime(2024, 6, 1)), [REPORT]),
        ((datetime(2024, 1, 1), datetime(2024, 12, 31)), [LUNCH, REPORT]),
        ((datetime(2025, 1, 1), None), []),
    ],
)
def test_date_range(engine, date_range, expected):
    assert subjects(engine.search('', date_range=date_range)) == expected


def test_result_fields(engine):
    [result] = engine.search('quarterly')
    assert result['sender'] == 'Alice Smith <alice@example.com>'
    assert '"Doe, John" <john@example.com>' in result['recipient']
    assert result['date'].strftime('%Y-%m-%d %H:%M') == '2024-03-05 10:00'
    assert len(result['id']) == 16


def test_max_results_and_bad_input(engine):
    assert len(engine.search('', max_results=1)) == 1
    with pytest.raises(ValueError):
        engine.search('x', fields=['body'])
    with pytest.raises(ValueError):
        engine.search('x', max_results=-1)


def test_reindexing_an_email_replaces_it(engine, data_dir):
    import json

    path = next(p for p in (data_dir / 'processed').glob('*.json') if 'summary' not in p.name)
    email = json.loads(path.read_text())
    engine.index_email(email)
    assert len(engine.search('')) == 2


@pytest.mark.parametrize(
    'raw,query,fields',
    [
        ('from:alice@example.com', 'alice@example.com', ['sender']),
        ('to:john', 'john', ['recipient']),
        ('subject:lunch', 'lunch', ['subject']),
        ('lunch', 'lunch', []),
    ],
)
def test_parse_query(raw, query, fields):
    assert parse_query(raw) == (query, fields)
