import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def mail_dir(tmp_path):
    """A copy of the fixture emails, so tests can add or remove files."""
    return Path(shutil.copytree(FIXTURES, tmp_path / 'mail'))


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / 'inbox'
