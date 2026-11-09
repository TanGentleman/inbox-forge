import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / 'fixtures'


def inbox_forge(*args, cwd):
    return subprocess.run(
        [sys.executable, '-m', 'inbox_forge', *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    'args, code, out',
    [
        ([], 2, 'usage: inbox-forge'),
        (['--help'], 0, 'usage: inbox-forge'),
        (['bogus'], 2, 'usage: inbox-forge'),
        (['ingest'], 2, ''),
        (['ingest', 'missing'], 1, ''),
        (['search'], 2, ''),
        (['search', 'x', '--after', '2024-13-01'], 2, 'Invalid date format'),
        (['search', 'x', '--before', 'yesterday'], 2, 'Invalid date format'),
        (['search', 'x', '--in', 'body'], 2, 'Invalid search fields: body'),
        (['search', 'x', '--in', 'subject,body'], 2, 'Invalid search fields: body'),
        (['search', 'anything'], 0, 'No matching emails found.'),
    ],
)
def test_exit_codes(tmp_path, args, code, out):
    result = inbox_forge(*args, cwd=tmp_path)
    assert result.returncode == code, result.stderr
    assert out in result.stdout


def test_readme_quick_start(tmp_path):
    """The README's commands, run from a fresh directory with the default ./data."""
    assert inbox_forge('ingest', str(FIXTURES), cwd=tmp_path).returncode == 0
    assert (tmp_path / 'data' / 'search_index' / 'emails.sqlite3').exists()

    out = inbox_forge('search', 'quarterly', cwd=tmp_path).stdout
    assert 'Found 1 matching emails' in out
    assert 'Subject: Quarterly report' in out

    out = inbox_forge('search', 'from:alice', '--after', '2024-01-01', cwd=tmp_path).stdout
    assert 'Subject: Quarterly report' in out
    assert 'Lunch' not in out
