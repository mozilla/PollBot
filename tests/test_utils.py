import pytest
from pollbot.utils import build_version_id, get_version_from_filename


VERSIONS = [
    ('54.0b1', '054000000b001'),
    ('53.0b99', '053000000b099'),
    ('45.9.0esr', '045009000x000'),
    ('54.0a2', '054000000a002'),
    ('54.0.1a2', '054000001a002'),
    ('2.48b1', '002048000b001'),
    ('2.48.3b1', '002048003b001'),
    ('50.0.1', '050000001r000'),
    ('50.0', '050000000r000'),
    ('50.0esr', '050000000x000'),
    ('50.0.12esr', '050000012x000'),
    ('2.50a1', '002050000a001'),
]


@pytest.mark.parametrize("arg,output", VERSIONS)
def test_parse_nightly_filename(arg, output):
    assert build_version_id(arg) == output


FILENAMES = [
    ('firefox-57.0a1.zh-TW.win64.zip', '57.0a1'),
]


@pytest.mark.parametrize("filename,version", FILENAMES)
def test_get_version_from_filename(filename, version):
    assert get_version_from_filename(filename) == version
