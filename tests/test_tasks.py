import datetime
import json
import os
from copy import deepcopy

import aiohttp
import asynctest
import pytest

from aioresponses import aioresponses

from pollbot.exceptions import TaskError
from pollbot.tasks import get_session, telemetry
from pollbot.tasks.archives import archives, partner_repacks, RELEASE_PLATFORMS
from pollbot.tasks.balrog import balrog_rules
from pollbot.tasks.buildhub import buildhub, BUILDHUB_SERVER
from pollbot.tasks.crash_stats import uptake as crash_stats_uptake, CRASH_STATS_SERVER
from pollbot.tasks.bedrock import release_notes, security_advisories, download_links, get_releases
from pollbot.tasks.bouncer import bouncer
from pollbot.tasks.product_details import (product_details, ongoing_versions,
                                           devedition_and_beta_in_sync)
from pollbot.views.utilities import heartbeat
from pollbot.utils import Status


HERE = os.path.dirname(__file__)


def get_json_body(filename):
    with open(filename) as f:
        return json.load(f)


LATEST_MOZILLA_CENTRAL_L10N_BODY = get_json_body(os.path.join(HERE, "fixtures",
                                                              "latest-mozilla-central-l10n.json"))
RELEASES_52_BODY = get_json_body(os.path.join(HERE, "fixtures", "releases_52.json"))
ALL_LOCALES_BODY = open(os.path.join(HERE, "fixtures", "all-locales.txt")).read()
SHIPPED_LOCALES_BODY = open(os.path.join(HERE, "fixtures", "shipped-locales.txt")).read()


class DeliveryTasksTest(asynctest.TestCase):
    def mock_platforms(self, platforms, working_body):
        for platform in platforms:
            url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/{}/'.format(platform)
            body = deepcopy(working_body)
            if platform.startswith('mac'):
                body['prefixes'].remove('ja/')
                body['prefixes'].append('ja-JP-mac/')
            self.mocked.get(url, status=200, body=json.dumps(body))

    async def setUp(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.addCleanup(self.session.close)

        self.mocked = aioresponses()
        self.mocked.start()
        self.addCleanup(self.mocked.stop)

    async def test_tasks_user_agent(self):
        self.mocked.get("http://localhost", status=200)
        with get_session() as session:
            assert session._default_headers['User-Agent'].startswith("PollBot/")

    async def test_get_releases_tasks_return_releases(self):
        url = 'https://www.mozilla.org/en-US/firefox/releases/'
        self.mocked.get(url, status=200, body='''
        <html data-latest-firefox="55.0">
          <div id="main-content">
            <ol reversed>
              <li>
                <strong><a href="../55.0/releasenotes/">55.0</a></strong>
              </li>
              <li>
                <strong><a href="../54.0/releasenotes/">54.0</a></strong>
                <ol>
                  <li><a href="../54.0.1/releasenotes/">54.0.1</a></li>
                </ol>
              </li>
              <li>
                <strong><a href="../53.0/releasenotes/">53.0</a></strong>
                <ol>
                  <li><a href="../53.0.2/releasenotes/">53.0.2</a></li>
                  <li><a href="../53.0.3/releasenotes/">53.0.3</a></li>
                </ol>
              </li>
              <li>
                <strong><a href="../9.0/releasenotes/">9.0</a></strong>
                <ol>
                  <li><a href="../9.0.1/releasenotes/">9.0.1</a></li>
                </ol>
              </li>
            </ol>
          </div>
        </html>
        ''')
        received = await get_releases('firefox')
        assert received == ["9.0", "9.0.1", "53.0", "53.0.2", "53.0.3", "54.0", "54.0.1", "55.0"]

    async def test_get_releases_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/firefox/releases/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await get_releases('firefox')
        assert str(excinfo.value) == 'Releases page not available  (404)'

    async def test_releasenotes_tasks_returns_true_if_present_for_beta(self):
        url = 'https://www.mozilla.org/en-US/firefox/56.0beta/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes('firefox', '56.0b2')
        assert received["status"] == Status.EXISTS.value

    async def test_releasenotes_tasks_returns_true_if_present(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value

    async def test_releasenotes_tasks_strip_esr_from_version_number(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.3.0/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes('firefox', '52.3.0esr')
        assert received["status"] == Status.EXISTS.value

    async def test_releasenotes_tasks_returns_false_if_absent(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=404)

        received = await release_notes('firefox', '52.0.2')
        assert received["status"] == Status.MISSING.value

    async def test_releasenotes_tasks_returns_false_if_redirect(self):
        url = 'https://www.mozilla.org/en-US/firefox/57.0/releasenotes/'
        self.mocked.get(url, status=302)

        received = await release_notes('firefox', '57.0')
        assert received["status"] == Status.MISSING.value

    async def test_archives_tasks_returns_task_error_if_mercurial_is_down(self):
        url = "https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales"
        self.mocked.get(url, status=502)
        url = 'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/'
        self.mocked.get(url, status=200, body=json.dumps(LATEST_MOZILLA_CENTRAL_L10N_BODY))

        with pytest.raises(TaskError) as excinfo:
            await archives('firefox', '57.0a1')
        assert str(excinfo.value) == (
            'https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales '
            'not available (HTTP 502)')

    async def test_archives_tasks_returns_incomplete_if_a_locale_is_missing_for_nightly(self):
        all_locales_plus_one = ALL_LOCALES_BODY + 'pt-BN\n'
        url = "https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales"
        self.mocked.get(url, status=200, body=all_locales_plus_one)
        url = 'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/'
        self.mocked.get(url, status=200, body=json.dumps(LATEST_MOZILLA_CENTRAL_L10N_BODY))

        received = await archives('firefox', '57.0a1')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == (
            'pt-BN locale is missing at '
            'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/')

    async def test_archives_tasks_returns_incomplete_if_a_file_is_missing_for_nightly(self):
        url = "https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales"
        self.mocked.get(url, status=200, body=ALL_LOCALES_BODY)

        latest_mozilla_central_minus_a_file = deepcopy(LATEST_MOZILLA_CENTRAL_L10N_BODY)
        del latest_mozilla_central_minus_a_file["files"][0]
        url = 'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/'
        self.mocked.get(url, status=200, body=json.dumps(latest_mozilla_central_minus_a_file))

        received = await archives('firefox', '57.0a1')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == (
            'Firefox Installer.ach.exe locale file is missing at '
            'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/')

    async def test_archives_tasks_returns_true_if_file_exists_nightly(self):
        url = "https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales"
        self.mocked.get(url, status=200, body=ALL_LOCALES_BODY)
        url = "https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/"
        self.mocked.get(url, status=200, body=json.dumps(LATEST_MOZILLA_CENTRAL_L10N_BODY))

        received = await archives('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value, received['message']

    async def test_archives_tasks_returns_false_if_absent_for_nightly(self):
        url = 'https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central-l10n/'
        self.mocked.get(url, status=404)

        received = await archives('firefox', '57.0a1')
        assert received["status"] == Status.MISSING.value

    async def test_archives_tasks_returns_true_if_folder_and_releases_exists(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)
        url = ('https://hg.mozilla.org/releases/mozilla-release/raw-file/'
               'FIREFOX_52_0_2_RELEASE/browser/locales/shipped-locales')
        self.mocked.get(url, status=200, body=SHIPPED_LOCALES_BODY)
        self.mock_platforms(RELEASE_PLATFORMS, RELEASES_52_BODY)

        received = await archives('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value

    async def test_archives_tasks_returns_incomplete_if_a_file_is_missing(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)
        url = ('https://hg.mozilla.org/releases/mozilla-release/raw-file/'
               'FIREFOX_52_0_2_RELEASE/browser/locales/shipped-locales')
        self.mocked.get(url, status=200, body=SHIPPED_LOCALES_BODY)

        release_52_minus_a_file = deepcopy(RELEASES_52_BODY)
        release_52_minus_a_file['prefixes'].pop()
        platform = RELEASE_PLATFORMS[0]
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/{}/'.format(platform)
        self.mocked.get(url, status=200, body=json.dumps(release_52_minus_a_file))
        self.mock_platforms(RELEASE_PLATFORMS[1:], RELEASES_52_BODY)

        received = await archives('firefox', '52.0.2')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == ('zh-TW for linux-i686 locale file is missing at '
                                       'https://archive.mozilla.org/pub/firefox/releases/52.0.2/')

    async def test_archives_tasks_returns_incomplete_if_ja_file_is_missing(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)
        url = ('https://hg.mozilla.org/releases/mozilla-release/raw-file/'
               'FIREFOX_52_0_2_RELEASE/browser/locales/shipped-locales')
        self.mocked.get(url, status=200, body=SHIPPED_LOCALES_BODY)

        release_52_minus_a_file = deepcopy(RELEASES_52_BODY)
        release_52_minus_a_file['prefixes'].remove('ja/')

        platform = RELEASE_PLATFORMS[2]
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/{}/'.format(platform)
        self.mocked.get(url, status=200, body=json.dumps(release_52_minus_a_file))

        self.mock_platforms(RELEASE_PLATFORMS[0:2] + RELEASE_PLATFORMS[3:], RELEASES_52_BODY)

        received = await archives('firefox', '52.0.2')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == ('ja-JP-mac for mac locale file is missing at '
                                       'https://archive.mozilla.org/pub/firefox/releases/52.0.2/')

    async def test_archives_tasks_returns_incomplete_if_a_locale_is_missing(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)
        url = ('https://hg.mozilla.org/releases/mozilla-release/raw-file/'
               'FIREFOX_52_0_2_RELEASE/browser/locales/shipped-locales')
        self.mocked.get(url, status=200, body=SHIPPED_LOCALES_BODY)

        release_52_minus_a_file = deepcopy(RELEASES_52_BODY)
        release_52_minus_a_file['prefixes'].pop()

        self.mock_platforms(RELEASE_PLATFORMS, release_52_minus_a_file)

        received = await archives('firefox', '52.0.2')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == ('zh-TW locale is missing at '
                                       'https://archive.mozilla.org/pub/firefox/releases/52.0.2/')

    async def test_archives_tasks_returns_false_if_absent(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=404)

        received = await archives('firefox', '52.0.2')
        assert received["status"] == Status.MISSING.value

    async def test_archives_tasks_returns_error_in_case_of_CDN_errors(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=502)

        with pytest.raises(TaskError) as excinfo:
            await archives('firefox', '52.0.2')
        assert str(excinfo.value) == 'Archive CDN not available (HTTP 502)'

    async def test_archives_tasks_returns_error_in_case_of_CDN_errors_later(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)
        url = ('https://hg.mozilla.org/releases/mozilla-release/raw-file/'
               'FIREFOX_52_0_2_RELEASE/browser/locales/shipped-locales')
        self.mocked.get(url, status=200, body=SHIPPED_LOCALES_BODY)

        platform = RELEASE_PLATFORMS[0]
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/{}/'.format(platform)
        self.mocked.get(url, status=502)
        self.mock_platforms(RELEASE_PLATFORMS[1:], RELEASES_52_BODY)

        with pytest.raises(TaskError) as excinfo:
            await archives('firefox', '52.0.2')
        assert str(excinfo.value) == (
            'Archive CDN not available; failing to get '
            'https://archive.mozilla.org/pub/firefox/releases/52.0.2/linux-i686/ (HTTP 502)')

    async def test_partner_repacks_tasks_returns_false_if_release_absent(self):
        url = 'https://archive.mozilla.org/pub/firefox/candidates/52.0.2-candidates/'
        self.mocked.get(url, status=404)

        received = await partner_repacks('firefox', '52.0.2')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == "No candidates found for that version."

    async def test_partner_repacks_tasks_returns_false_if_partner_repacks_folder_absent(self):
        url = 'https://archive.mozilla.org/pub/firefox/candidates/52.0.2-candidates/'
        self.mocked.get(url, status=200, body=json.dumps({"prefixes": ["build1/", "build2/"]}))

        url = 'https://archive.mozilla.org/pub/firefox/candidates/52.0.2-candidates/build2/'
        self.mocked.get(url, status=200, body=json.dumps({"prefixes": ["linux/", "mac/"]}))

        received = await partner_repacks('firefox', '52.0.2')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == ("No partner-repacks in https://archive.mozilla.org/"
                                       "pub/firefox/candidates/52.0.2-candidates/build2/")

    async def test_partner_repacks_tasks_returns_true_if_partner_repacks_folder_present(self):
        url = 'https://archive.mozilla.org/pub/firefox/candidates/52.0.2-candidates/'
        self.mocked.get(url, status=200, body=json.dumps({"prefixes": ["build1/", "build2/"]}))

        url = 'https://archive.mozilla.org/pub/firefox/candidates/52.0.2-candidates/build2/'
        self.mocked.get(url, status=200, body=json.dumps({"prefixes": ["partner-repacks/"]}))

        received = await partner_repacks('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == ("Partner-repacks found in https://archive.mozilla.org/"
                                       "pub/firefox/candidates/52.0.2-candidates/build2/")

    async def test_crash_stats_tasks_returns_error_if_no_hits_for_the_channel(self):
        url = '{}/ProductVersions/?active=true&build_type=RELEASE&product=firefox'
        url = url.format(CRASH_STATS_SERVER)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version":"54.0"}, {"version":"52.0.2"}], "total": 2}')

        date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body='{"hits": [], "total": 0}')

        date = (datetime.date.today() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body='{"hits": [], "total": 0}')

        received = await crash_stats_uptake('firefox', '52.0.2')
        assert received["status"] == Status.ERROR.value
        assert received["message"] == "No crash-stats ADI info for version ['54.0', '52.0.2']"

    async def test_crash_stats_tasks_tries_the_day_before_if_no_hits_for_the_channel(self):
        url = '{}/ProductVersions/?active=true&build_type=RELEASE&product=firefox'
        url = url.format(CRASH_STATS_SERVER)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version":"54.0"}, {"version":"52.0.2"}], "total": 2}')

        date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body='{"hits": [], "total": 0}')

        date = (datetime.date.today() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body=json.dumps({
            "hits": [{"version": "52.0", "adi_count": 500},
                     {"version": "52.0.1", "adi_count": 3000},
                     {"version": "52.0.2", "adi_count": 5000}],
            "total": 3}))

        received = await crash_stats_uptake('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == "Crash-Stats uptake for version 52.0.2 is 58.82%"

    async def test_crash_stats_tasks_returns_error_if_no_hits_for_the_given_version(self):
        url = '{}/ProductVersions/?active=true&build_type=RELEASE&product=firefox'
        url = url.format(CRASH_STATS_SERVER)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version":"54.0"}, {"version":"52.0.2"}], "total": 2}')

        date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version": "54.0", "adi_count": 120}], "total": 1}')
        received = await crash_stats_uptake('firefox', '52.0.2')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == "No crash-stats ADI hits for version 52.0.2"

    async def test_crash_stats_tasks_returns_incomplete_if_ratio_is_low(self):
        url = '{}/ProductVersions/?active=true&build_type=RELEASE&product=firefox'
        url = url.format(CRASH_STATS_SERVER)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version":"54.0"}, {"version":"52.0.2"}], "total": 2}')

        date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body=json.dumps({
            "hits": [{"version": "52.0", "adi_count": 500},
                     {"version": "52.0.1", "adi_count": 5000},
                     {"version": "52.0.2", "adi_count": 3000}],
            "total": 3}))
        body = await crash_stats_uptake('firefox', '52.0.2')
        assert body["status"] == Status.INCOMPLETE.value
        assert body["message"] == "Crash-Stats uptake for version 52.0.2 is 35.29%"

    async def test_crash_stats_tasks_returns_exists_if_ratio_is_high(self):
        url = '{}/ProductVersions/?active=true&build_type=RELEASE&product=firefox'
        url = url.format(CRASH_STATS_SERVER)
        self.mocked.get(url, status=200,
                        body='{"hits": [{"version":"54.0"}, {"version":"52.0.2"}], "total": 2}')

        date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        url = ('{}/ADI/?start_date={}&end_date={}&platforms=Windows&platforms=Linux&'
               'platforms=Mac%20OS%20X&product=firefox&versions=54.0&versions=52.0.2')
        url = url.format(CRASH_STATS_SERVER, date, date)
        self.mocked.get(url, status=200, body=json.dumps({
            "hits": [{"version": "52.0", "adi_count": 500},
                     {"version": "52.0.1", "adi_count": 3000},
                     {"version": "52.0.2", "adi_count": 5000}],
            "total": 3}))
        body = await crash_stats_uptake('firefox', '52.0.2')
        assert body["status"] == Status.EXISTS.value
        assert body["message"] == "Crash-Stats uptake for version 52.0.2 is 58.82%"

    async def test_download_links_tasks_returns_true_if_version_matches(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_true_if_version_matches_for_beta(self):
        url = 'https://www.mozilla.org/fr/firefox/channel/desktop/'
        self.mocked.get(url, status=200, body='''
        <html>
          <div id="desktop-beta-download">
            <ul class="download-list">
              <li class="os_linux64">
                <a class="download-link"
                   href="https://download.mozilla.org/?product=firefox-beta-SSL&amp;os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')
        url = 'https://download.mozilla.org/?product=firefox-beta-SSL&os=linux64'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/releases"
            "/57.0b13/linux-x86_64/en-US/firefox-57.0b13.tar.bz2"})

        received = await download_links('firefox', '57.0b13')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_true_if_version_matches_for_nightly(self):
        url = 'https://www.mozilla.org/fr/firefox/channel/desktop/'
        self.mocked.get(url, status=200, body='''
        <html>
          <div id="desktop-nightly-download">
            <ul class="download-list">
              <li class="os_linux64">
                <a class="download-link"
                   href="https://download.mozilla.org/?product=firefox-nightly-latest-l10n-ssl&os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')
        url = 'https://download.mozilla.org/?product=firefox-nightly-latest-l10n-ssl&os=linux64'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/nightly"
            "/latest-mozilla-central-l10n/firefox-57.0a1.en-US.linux-x86_64.tar.bz2"})

        received = await download_links('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_true_if_older_version_for_beta(self):
        url = 'https://www.mozilla.org/fr/firefox/channel/desktop/'
        self.mocked.get(url, status=200, body='''
        <html>
          <div id="desktop-beta-download">
            <ul class="download-list">
              <li class="os_linux64">
                <a class="download-link"
                   href="https://download.mozilla.org/?product=firefox-beta-SSL&amp;os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')
        url = 'https://download.mozilla.org/?product=firefox-beta-SSL&os=linux64'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/releases"
            "/57.0b13/linux-x86_64/en-US/firefox-57.0b13.tar.bz2"})

        received = await download_links('firefox', '56.0b1')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_true_if_version_matches_esr(self):
        url = 'https://www.mozilla.org/en-US/firefox/organizations/all/'
        self.mocked.get(url, status=200, body='<html data-esr-versions="52.3.0"></html>')

        received = await download_links('firefox', '52.3.0esr')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_true_if_older_version(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '52.0')
        assert received["status"] == Status.EXISTS.value

    async def test_download_links_tasks_returns_false_if_newer_version(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '54.0')
        assert received["status"] == Status.MISSING.value

    async def test_download_links_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await download_links('firefox', '54.0')
        assert str(excinfo.value) == 'Download page not available  (404)'

    async def test_security_advisories_tasks_returns_missing_for_beta(self):
        received = await security_advisories('firefox', '56.0b2')
        assert received["status"] == Status.MISSING.value

    async def test_security_advisories_tasks_returns_missing_for_nightly(self):
        received = await security_advisories('firefox', '56.0a2')
        assert received["status"] == Status.MISSING.value

    async def test_security_advisories_tasks_returns_true_if_version_matches(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '52.0.2')
        assert received["status"] == Status.EXISTS.value

    async def test_security_advisories_tasks_returns_true_if_version_matches_esr(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-esr-versions="52.3.0"></html>')

        received = await security_advisories('firefox', '52.3.0esr')
        assert received["status"] == Status.EXISTS.value

    async def test_security_advisories_tasks_returns_true_if_older_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '52.0')
        assert received["status"] == Status.EXISTS.value

    async def test_security_advisories_tasks_returns_false_if_newer_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '54.0')
        assert received["status"] == Status.MISSING.value

    async def test_security_advisories_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await security_advisories('firefox', '54.0')
        assert str(excinfo.value) == 'Security advisories page not available  (404)'

    async def test_product_details_tasks_returns_true_if_present_for_nightly(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        body = {
            "FIREFOX_NIGHTLY": "57.0a1",
            "FIREFOX_AURORA": "54.0a2",
            "FIREFOX_ESR": "52.3.0esr",
            "FIREFOX_ESR_NEXT": "",
            "LATEST_FIREFOX_DEVEL_VERSION": "55.0b13",
            "FIREFOX_DEVEDITION": "55.0b13",
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": "55.0b14",
            "LATEST_FIREFOX_VERSION": "55.0"
        }
        self.mocked.get(url, status=200, body=json.dumps(body))

        received = await product_details('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value

    async def test_product_details_tasks_returns_true_if_not_present_for_nightly(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        body = {
            "FIREFOX_NIGHTLY": "57.0a1",
            "FIREFOX_AURORA": "54.0a2",
            "FIREFOX_ESR": "52.3.0esr",
            "FIREFOX_ESR_NEXT": "",
            "LATEST_FIREFOX_DEVEL_VERSION": "55.0b13",
            "FIREFOX_DEVEDITION": "55.0b13",
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": "55.0b14",
            "LATEST_FIREFOX_VERSION": "55.0"
        }
        self.mocked.get(url, status=200, body=json.dumps(body))

        received = await product_details('firefox', '58.0a1')
        assert received["status"] == Status.MISSING.value

    async def test_product_details_tasks_returns_true_if_present(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=200, body=json.dumps({"releases": {"firefox-52.0": {}}}))

        received = await product_details('firefox', '52.0')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == "We found product-details information about version 52.0"

    async def test_product_details_tasks_returns_false_if_absent(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=200, body=json.dumps({"releases": {"firefox-52.0": {}}}))

        received = await product_details('firefox', '54.0')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == (
            "We did not find product-details information about version 54.0")

    async def test_product_details_tasks_returns_error_if_error(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await product_details('firefox', '54.0')
        assert str(excinfo.value) == 'Product Details info not available (HTTP 404)'

    async def test_devedition_version_tasks_returns_false_if_not_in_sync(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        body = {
            "FIREFOX_NIGHTLY": "57.0a1",
            "FIREFOX_AURORA": "54.0a2",
            "FIREFOX_ESR": "52.3.0esr",
            "FIREFOX_ESR_NEXT": "",
            "LATEST_FIREFOX_DEVEL_VERSION": "55.0b14",
            "FIREFOX_DEVEDITION": "55.0rc1",
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": "55.0b14",
            "LATEST_FIREFOX_VERSION": "55.0"
        }
        self.mocked.get(url, status=200, body=json.dumps(body))

        received = await devedition_and_beta_in_sync('firefox', '55.0b14')
        assert received["status"] == Status.MISSING.value

    async def test_devedition_version_tasks_returns_true_if_in_sync(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        body = {
            "FIREFOX_NIGHTLY": "57.0a1",
            "FIREFOX_AURORA": "54.0a2",
            "FIREFOX_ESR": "52.3.0esr",
            "FIREFOX_ESR_NEXT": "",
            "LATEST_FIREFOX_DEVEL_VERSION": "56.0b7",
            "FIREFOX_DEVEDITION": "56.0b7",
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": "55.0b14",
            "LATEST_FIREFOX_VERSION": "55.0"
        }
        self.mocked.get(url, status=200, body=json.dumps(body))

        received = await devedition_and_beta_in_sync('firefox', '56.0b7')
        assert received["status"] == Status.EXISTS.value

    async def test_devedition_version_tasks_returns_error_if_error(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await devedition_and_beta_in_sync('firefox', '56.0b7')
        assert str(excinfo.value) == 'Product Details info not available (HTTP 404)'

    async def test_devedition_version_tasks_returns_missing_for_other_channels(self):
        received = await devedition_and_beta_in_sync('firefox', '54.0')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == "No devedition and beta check for 'release' releases"

    async def test_bouncer_tasks_returns_true_if_version_matches_for_nightly(self):
        url = 'https://www.mozilla.org/fr/firefox/channel/desktop/'
        self.mocked.get(url, status=200, body='''
        <html>
          <div id="desktop-nightly-download">
            <ul class="download-list">
              <li class="os_linux64">
                <a class="download-link"
                   href="https://download.mozilla.org/?product=firefox-nightly-latest-l10n-ssl&os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')
        url = 'https://download.mozilla.org/?product=firefox-nightly-latest-l10n-ssl&os=linux64'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/nightly"
            "/latest-mozilla-central-l10n/firefox-57.0a1.en-US.linux-x86_64.tar.bz2"})

        received = await bouncer('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value

    async def test_bouncer_tasks_returns_true_if_version_matches_for_beta(self):
        url = 'https://www.mozilla.org/fr/firefox/channel/desktop/'
        self.mocked.get(url, status=200, body='''
        <html>
          <div id="desktop-beta-download">
            <ul class="download-list">
              <li class="os_linux64">
                <a class="download-link"
                   href="https://download.mozilla.org/?product=firefox-beta-ssl&amp;os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')
        url = 'https://download.mozilla.org/?product=firefox-beta-ssl&os=linux64'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/releases"
            "/57.0b13/linux-x86_64/en-US/firefox-57.0b13.tar.bz2"})

        received = await bouncer('firefox', '57.0b13')
        assert received["status"] == Status.EXISTS.value

    async def test_bouncer_tasks_returns_true_if_version_matches_for_release(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='''
<html>
<table>
 <tr id="fr">
  <td class="download linux64">
   <a href="https://download.mozilla.org/?product=firefox-latest-ssl&amp;os=linux64&amp;lang=fr">
    Download
   </a>
  </td>
 </tr>
</table>
</html>''')
        url = 'https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&amp;lang=fr'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/releases"
            "/57.0/linux-x86_64/fr/firefox-57.0.tar.bz2"})

        received = await bouncer('firefox', '57.0')
        assert received["status"] == Status.EXISTS.value

    async def test_bouncer_tasks_returns_true_if_version_matches_for_esr(self):
        url = 'https://www.mozilla.org/en-US/firefox/organizations/all/'
        self.mocked.get(url, status=200, body='''
<html>
<table>
 <tr id="fr">
  <td class="download linux64">
   <a href="https://download.mozilla.org/?product=firefox-esr-ssl&amp;os=linux64&amp;lang=fr">
    Download
   </a>
  </td>
 </tr>
</table>
</html>''')
        url = 'https://download.mozilla.org/?product=firefox-esr-ssl&os=linux64&amp;lang=fr'
        self.mocked.get(url, status=302, headers={
            "Location": "https://download-installer.cdn.mozilla.net/pub/firefox/releases/"
            "52.5.0esr/linux-x86_64/fr/firefox-52.5.0esr.tar.bz2"})

        received = await bouncer('firefox', '52.5.0esr')
        assert received["status"] == Status.EXISTS.value

    async def test_failing_heartbeat(self):
        # Archive
        url = 'https://archive.mozilla.org/pub/firefox/releases/'
        self.mocked.get(url, status=404)

        # Bedrock
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=404)

        # Bouncer
        url = 'https://download.mozilla.org/'
        self.mocked.get(url, status=404)

        # Balrog
        url = 'https://aus-api.mozilla.org/__heartbeat__'
        self.mocked.get(url, status=404)

        # Buildhub
        url = '{}/__heartbeat__'.format(BUILDHUB_SERVER)
        self.mocked.get(url, status=404)

        # Crash Stats
        url = 'https://crash-stats.mozilla.com/monitoring/healthcheck/'
        self.mocked.get(url, status=404)

        # Product Details
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=404)

        # Product Details
        url = 'https://sql.telemetry.mozilla.org/api/data_sources/1/version'
        self.mocked.get(url, status=404)

        resp = await heartbeat(None)
        assert json.loads(resp.body.decode()) == {
            "archive": False,
            "balrog": False,
            "bouncer": False,
            "bedrock": False,
            "buildhub": False,
            "crash-stats": False,
            "product-details": False,
            "telemetry": False,
        }
        assert resp.status == 503

    async def test_get_ongoing_versions_return_ongoing_versions(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        body = {
            "FIREFOX_NIGHTLY": "57.0a1",
            "FIREFOX_AURORA": "54.0a2",
            "FIREFOX_ESR": "52.3.0esr",
            "FIREFOX_ESR_NEXT": "",
            "LATEST_FIREFOX_DEVEL_VERSION": "55.0b13",
            "FIREFOX_DEVEDITION": "55.0b13",
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": "55.0b14",
            "LATEST_FIREFOX_VERSION": "55.0"
        }
        self.mocked.get(url, status=200, body=json.dumps(body))
        received = await ongoing_versions('firefox')
        assert received == {
            "esr": "52.3.0esr",
            "release": "55.0",
            "beta": "55.0b13",
            "devedition": "55.0b13",
            "nightly": "57.0a1",
        }

    async def test_get_ongoing_versions_returns_error_if_error(self):
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await ongoing_versions('firefox')
        assert str(excinfo.value) == 'Product Details info not available (HTTP 404)'

    async def test_balrog_rules_tasks_returns_error_if_platform_is_missing(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-mozilla-central-nightly-latest'
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-mozilla-central-nightly-latest'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {"foo": {}, "bar": {}}}))

        with pytest.raises(TaskError) as excinfo:
            await balrog_rules('firefox', '57.0a1')
        assert str(excinfo.value) == "No platform with locales was found in ['bar', 'foo']"

    async def test_balrog_rules_tasks_returns_missing_if_mapping_is_wrong(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-mozilla-central-nightly'
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-mozilla-central-nightly'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {
            "linux": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}}}}))

        received = await balrog_rules('firefox', '57.0a1')
        assert received['status'] == Status.MISSING.value
        assert received["message"] == ('Balrog rule is configured for '
                                       'Firefox-mozilla-central-nightly (20170922221002) '
                                       'instead of "Firefox-mozilla-central-nightly-latest"')

    async def test_balrog_rules_tasks_returns_incomplete_if_buildID_are_not_matching(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-mozilla-central-nightly-latest'
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-mozilla-central-nightly-latest'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {
            "linux": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
            "mac": {"locales": {"de": {"buildID": "20170921221002", "appVersion": "57.0a1"}}},
        }}))

        received = await balrog_rules('firefox', '57.0a1')
        assert received["message"] == ('Balrog rule is configured for '
                                       'Firefox-mozilla-central-nightly-latest '
                                       '(20170921221002, 20170922221002) '
                                       'platform mac with build ID 20170921221002 seem outdated.')
        assert received['status'] == Status.INCOMPLETE.value

    async def test_balrog_rules_tasks_returns_exists_if_buildID_are_matching(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-mozilla-central-nightly-latest',
            'backgroundRate': 100
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-mozilla-central-nightly-latest'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {
            "linux": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
            "mac": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
        }}))

        received = await balrog_rules('firefox', '57.0a1')
        assert received["message"] == ('Balrog rule is configured for the latest '
                                       'Nightly 57.0a1 build (20170922221002) '
                                       'with an update rate of 100%')
        assert received['status'] == Status.EXISTS.value

    async def test_balrog_rules_tasks_returns_incomplete_if_nightly_backgroundRate_is_low(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-mozilla-central-nightly-latest',
            'backgroundRate': 50
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-mozilla-central-nightly-latest'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {
            "linux": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
            "mac": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
        }}))

        received = await balrog_rules('firefox', '57.0a1')
        assert received["message"] == ('Balrog rule is configured for the latest '
                                       'Nightly 57.0a1 build (20170922221002) '
                                       'with an update rate of 50%')
        assert received['status'] == Status.INCOMPLETE.value

    async def test_balrog_rules_tasks_returns_incomplete_if_release_backgroundRate_is_low(self):
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-release'
        self.mocked.get(url, status=200, body=json.dumps({
            'mapping': 'Firefox-56.0-build6',
            'backgroundRate': 50
        }))
        url = 'https://aus-api.mozilla.org/api/v1/releases/Firefox-56.0-build6'
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {
            "linux": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
            "mac": {"locales": {"de": {"buildID": "20170922221002", "appVersion": "57.0a1"}}},
        }}))

        received = await balrog_rules('firefox', '56.0')
        assert received["message"] == ('Balrog rule has been updated for Firefox-56.0-build6 '
                                       '(20170922221002) with an update rate of 50%')
        assert received['status'] == Status.INCOMPLETE.value

    def _mock_buildhub_search(self, build_id="20171009192146"):
        url = "{}/buckets/build-hub/collections/releases/search".format(BUILDHUB_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "aggregations": {
                "by_version": {
                    "buckets": [
                        {
                            "doc_count": 433,
                            "key": build_id
                        }
                    ],
                }
            }}))

    async def test_buildhub_task_returns_missing_if_release_is_missing(self):
        url = "{}/buckets/build-hub/collections/releases/search".format(BUILDHUB_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            'aggregations': {
                "by_version": {
                    "buckets": []
                    }
                }
        }))
        received = await buildhub('firefox', '57.0a1')
        assert received['status'] == Status.MISSING.value
        assert received["message"] == ("Buildhub does not contain any information "
                                       "about this release yet.")

    async def test_buildhub_task_returns_incomplete_if_nightly_too_old(self):
        self._mock_buildhub_search("20171009192146")
        received = await buildhub('firefox', '58.0a1')
        assert received['status'] == Status.INCOMPLETE.value
        assert received["message"] == ("Build IDs for this release: 20171009192146")

    async def test_buildhub_task_returns_exists_if_nightly_is_fresh(self):
        build_id = datetime.date.today().strftime('%Y%m%d%H%M%S')
        self._mock_buildhub_search(build_id)
        received = await buildhub('firefox', '58.0a1')
        assert received['status'] == Status.EXISTS.value
        assert received["message"] == "Build IDs for this release: {}".format(build_id)

    async def test_buildhub_task_returns_exists_if_release_was_found(self):
        self._mock_buildhub_search("20170914024831")
        received = await buildhub('firefox', '56.0b12')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == "Build IDs for this release: 20170914024831"

    def _telemetry_mock_release_query(self, body=None):
        url = ("{}/api/queries/search?q="
               "Uptake+Firefox+RELEASE+57.0+%2820171009192146%29&include_drafts=true")
        url = url.format(telemetry.TELEMETRY_SERVER)
        if body is None:
            body = [{
                "latest_query_data_id": 5678,
                "id": 40197,
                "name": "Uptake Firefox RELEASE 57.0 (20171009192146)"
            }]
        self.mocked.get(url, status=200, body=json.dumps(body))

    def _telemetry_mock_nightly_query(self, body=None):
        if body is None:
            body = [{
                "latest_query_data_id": 5678,
                "id": 40197,
                "name": "Uptake Firefox NIGHTLY 57.0a1 20170920"
            }]

        url = ("{}/api/queries/search?q=Uptake+Firefox+NIGHTLY+57.0a1+"
               "%2820170920220431%2C+20170920111019%2C+20170920100426%29&include_drafts=true")
        url = url.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=200, body=json.dumps(body))

    def _telemetry_mock_query_result(self, body):
        url = '{}/api/query_results/5678'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=200, body=json.dumps(body))

    def _telemetry_mock_nightly_build_ids(self, body=None):
        url = '{}/api/queries/{}'
        url = url.format(telemetry.TELEMETRY_SERVER, telemetry.NIGHTLY_BUILD_IDS["57.0a1"])
        self.mocked.get(url, status=200, body=json.dumps({
            "latest_query_data_id": 1234
        }))

        if body is None:
            body = {
                "query_result": {"data": {"rows": [
                    {"build_id": "20170920220431"},
                    {"build_id": "20170920111019"},
                    {"build_id": "20170920100426"},
                    {"build_id": "20170919220202"},
                    {"build_id": "20170919110626"}
                ]}}
            }

        url = '{}/api/query_results/1234'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=200, body=json.dumps(body))

    async def test_telemetry_update_uptake_tasks_returns_error_for_previous_nightly(self):
        received = await telemetry.update_parquet_uptake('firefox', '56.0a1')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == "Telemetry update-parquet metrics landed in Firefox Quantum"

    async def test_telemetry_update_uptake_tasks_returns_error_for_unsupported_nightly(self):
        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0a2')
        assert str(excinfo.value) == 'Please configure Build IDs query for 57.0a2'

    async def test_telemetry_update_uptake_tasks_returns_error_for_unavailable_query(self):
        url = '{}/api/queries/{}'
        url = url.format(telemetry.TELEMETRY_SERVER, telemetry.NIGHTLY_BUILD_IDS["57.0a1"])
        self.mocked.get(url, status=502)

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert str(excinfo.value) == 'Query 40223 unavailable (HTTP 502)'

    async def test_telemetry_update_uptake_tasks_returns_incomplete_for_no_result(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query([{
            "latest_query_data_id": None,
            "id": 40197,
            "name": "Uptake Firefox NIGHTLY 57.0a1 20170920"
        }])

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == ("Query still processing.")

    async def test_telemetry_update_uptake_tasks_returns_error_for_empty_results(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query()
        self._telemetry_mock_query_result({
            "query_result": {"data": {"rows": []}}
        })

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.ERROR.value
        assert received["message"] == ("No result found for your query.")

    async def test_telemetry_update_uptake_tasks_returns_error_for_unavailable_query_results(self):
        url = '{}/api/queries/{}'
        url = url.format(telemetry.TELEMETRY_SERVER, telemetry.NIGHTLY_BUILD_IDS["57.0a1"])
        self.mocked.get(url, status=200, body=json.dumps({
            "latest_query_data_id": 1234
        }))
        url = '{}/api/query_results/1234'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=502)

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert str(excinfo.value) == 'Query Result 1234 unavailable (HTTP 502)'

    async def test_telemetry_update_uptake_tasks_returns_incomplete_for_low_nightly_uptake(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query()
        self._telemetry_mock_query_result({
            "query_result": {"data": {"rows": [
                {"ratio": 0.4532, "updated": 19074, "total": 42088}
            ]}}
        })

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == ("Telemetry uptake for version 57.0a1 "
                                       "(20170920220431, 20170920111019, 20170920100426) "
                                       "is 45.32%")

    async def test_telemetry_update_uptake_tasks_should_ignore_copied_queries(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query([{
            "latest_query_data_id": 123456789,
            "id": 40198,
            "name": "Copy of (#40197) Uptake Firefox NIGHTLY 57.0a1 20170920"
        }, {
            "latest_query_data_id": 5678,
            "id": 40197,
            "name": "Uptake Firefox NIGHTLY 57.0a1 20170920"
        }])
        self._telemetry_mock_query_result({
            "query_result": {"data": {"rows": [
                {"ratio": 0.65432, "updated": 27236, "total": 42088}
            ]}}
        })

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == ("Telemetry uptake for version 57.0a1 "
                                       "(20170920220431, 20170920111019, 20170920100426) "
                                       "is 65.43%")

    async def test_telemetry_update_uptake_tasks_returns_exists_for_high_nightly_uptake(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query()
        url = '{}/api/query_results/5678'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=200, body=json.dumps({
            "query_result": {"data": {"rows": [
                {"ratio": 0.65432, "updated": 27236, "total": 42088}
            ]}}
        }))

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.EXISTS.value
        assert received["message"] == ("Telemetry uptake for version 57.0a1 "
                                       "(20170920220431, 20170920111019, 20170920100426) "
                                       "is 65.43%")

    async def test_telemetry_update_uptake_tasks_returns_missing_for_no_search_query(self):
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query()
        url = '{}/api/query_results/5678'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.get(url, status=404)

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.MISSING.value
        assert received["message"] == "Query Result 5678 unavailable (HTTP 404)"

    async def test_telemetry_update_uptake_tasks_returns_incomplete_for_low_release_uptake(self):
        self._mock_buildhub_search()
        self._telemetry_mock_release_query()
        self._telemetry_mock_query_result({
            "query_result": {"data": {"rows": [
                {"ratio": 0.4532, "updated": 19074, "total": 42088}
            ]}}
        })

        received = await telemetry.update_parquet_uptake('firefox', '57.0')
        assert received["status"] == Status.INCOMPLETE.value
        message = "Telemetry uptake for version 57.0 (20171009192146) is 45.32%"
        assert received["message"] == message

    async def test_telemetry_update_uptake_tasks_returns_incomplete_for_high_release_uptake(self):
        self._mock_buildhub_search()
        self._telemetry_mock_release_query()
        self._telemetry_mock_query_result({
            "query_result": {"data": {"rows": [
                {"ratio": 0.65432, "updated": 27236, "total": 42088}
            ]}}
        })

        received = await telemetry.update_parquet_uptake('firefox', '57.0')
        assert received["status"] == Status.EXISTS.value
        message = "Telemetry uptake for version 57.0 (20171009192146) is 65.43%"
        assert received["message"] == message

    async def test_telemetry_update_uptake_creates_the_query_if_not_found_for_nightly(self):
        self._mock_buildhub_search()
        self._telemetry_mock_nightly_build_ids()
        self._telemetry_mock_nightly_query([])

        url = '{}/api/queries'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "id": 1234
        }))

        url = '{}/api/query_results'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "id": 5678
        }))

        received = await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == (
            "Telemetry uptake calculation for version 57.0a1 "
            "(20170920220431, 20170920111019, 20170920100426) is in progress"
        )

    async def test_telemetry_update_uptake_creates_the_query_if_null_body(self):
        url = '{}/api/queries/{}'
        url = url.format(telemetry.TELEMETRY_SERVER, telemetry.NIGHTLY_BUILD_IDS["57.0a1"])
        self.mocked.get(url, status=200, body=json.dumps({}))

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert str(excinfo.value) == "Couldn't find any build matching."

    async def test_telemetry_update_uptake_creates_the_query_if_no_results(self):
        self._telemetry_mock_nightly_build_ids({
            "query_result": {"data": {"rows": []}}
        })

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0a1')
        assert str(excinfo.value) == "Couldn't find any build matching."

    async def test_telemetry_update_uptake_creates_the_query_if_not_found_for_release(self):
        self._mock_buildhub_search()
        self._telemetry_mock_release_query([])

        url = '{}/api/queries'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "id": 1234
        }))

        url = '{}/api/query_results'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "id": 5678
        }))

        received = await telemetry.update_parquet_uptake('firefox', '57.0')
        assert received["status"] == Status.INCOMPLETE.value
        assert received["message"] == (
            "Telemetry uptake calculation for version 57.0 (20171009192146) is in progress"
        )

    async def test_telemetry_update_uptake_return_error_if_the_query_creation_failed(self):
        self._mock_buildhub_search()
        self._telemetry_mock_release_query([])

        url = '{}/api/queries'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=403)

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0')
        message = 'Unable to create the new query for 57.0 (20171009192146) (HTTP 403)'
        assert str(excinfo.value) == message

    async def test_telemetry_update_uptake_return_error_if_the_query_execution_failed(self):
        self._mock_buildhub_search()
        self._telemetry_mock_release_query([])

        url = '{}/api/queries'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=200, body=json.dumps({
            "id": 1234
        }))

        url = '{}/api/query_results'.format(telemetry.TELEMETRY_SERVER)
        self.mocked.post(url, status=403)

        with pytest.raises(TaskError) as excinfo:
            await telemetry.update_parquet_uptake('firefox', '57.0')
        message = 'Unable to execute the query n°1234 for 57.0 (20171009192146) (HTTP 403)'
        assert str(excinfo.value) == message
