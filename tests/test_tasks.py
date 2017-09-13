import json
import os
from copy import deepcopy

import aiohttp
import asynctest
import pytest

from aioresponses import aioresponses

from pollbot.exceptions import TaskError
from pollbot.tasks import get_session
from pollbot.tasks.archives import archives, RELEASE_PLATFORMS
from pollbot.tasks.balrog import balrog_rules
from pollbot.tasks.bedrock import release_notes, security_advisories, download_links, get_releases
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
                   href="https://download.mozilla.org/?product=firefox-56.0b1-SSL&amp;os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')

        received = await download_links('firefox', '56.0b1')
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
                   href="https://download.mozilla.org/?product=firefox-56.0b1-SSL&amp;os=linux64"
                   >Téléchargement</a>
              </li>
            </ul>
          </div>
        </html>''')

        received = await download_links('firefox', '55.0b1')
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

    async def test_product_details_tasks_returns_false_if_absent(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=200, body=json.dumps({"releases": {"firefox-52.0": {}}}))

        received = await product_details('firefox', '54.0')
        assert received["status"] == Status.MISSING.value

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

    async def test_failing_heartbeat(self):
        # Archive
        url = 'https://archive.mozilla.org/pub/firefox/releases/'
        self.mocked.get(url, status=404)

        # Bedrock
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=404)

        # Product Details
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=404)

        # Balrog
        url = 'https://aus-api.mozilla.org/__heartbeat__'
        self.mocked.get(url, status=404)

        resp = await heartbeat(None)
        assert json.loads(resp.body.decode()) == {
            "archive": False,
            "bedrock": False,
            "product-details": False,
            "balrog": False,
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
        self.mocked.get(url, status=200, body=json.dumps({'platforms': {}}))

        with pytest.raises(TaskError) as excinfo:
            await balrog_rules('firefox', '57.0a1')
        assert str(excinfo.value) == 'Linux x86_64 platform not found in []'
