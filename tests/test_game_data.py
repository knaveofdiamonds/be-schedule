from pathlib import Path

import pytest

import game_data as subject


@pytest.fixture
def family_raw_xml():
    dummy_data = Path(__file__).parent / 'family.xml'

    with dummy_data.open() as f:
        xml = f.read()

    return xml


def test_entries_from_raw_family_xml(family_raw_xml):
    result = subject.entries_from_raw_family_xml(family_raw_xml)

    assert result == [114139, 17132, 63170]
