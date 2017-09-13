import pytest
from pollbot.tasks.archives import verdict
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


VERDICTS = [
    ([], [], "The archive exists at url and all 2 locales are present "
     "for all platforms (linux-i686, linux-x86_64, mac, win32, win64)"),
    (['fr'], [], 'fr locale is missing at url'),
    (['fr', 'en'], [], 'en, fr locales are missing at url'),
    ([], ['Firefox Installer.fr.exe'], 'Firefox Installer.fr.exe locale file is missing at url'),
    ([], ['firefox.fr.dmg', 'firefox.fr.tgz'],
     'firefox.fr.dmg, firefox.fr.tgz locale files are missing at url'),
    (['be'], ['Firefox.exe'], 'be locale and Firefox.exe locale file are missing at url'),
]


@pytest.mark.parametrize("missing_locales,missing_files,message", VERDICTS)
def test_verdict_can_handle_pluralization(missing_locales, missing_files, message):
    _, explaination = verdict('url', ['1', '2'], missing_locales, missing_files)
    assert explaination == message
