import json

import aiohttp
import asynctest
import pytest

from aioresponses import aioresponses

from pollbot.exceptions import TaskError
from pollbot.tasks import get_session
from pollbot.tasks.archives import archives
from pollbot.tasks.bedrock import release_notes, security_advisories, download_links
from pollbot.tasks.product_details import product_details
from pollbot.views.utilities import heartbeat


class DeliveryTasksTest(asynctest.TestCase):
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

    async def test_releasenotes_tasks_returns_true_if_present(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes('firefox', '52.0.2')
        assert received is True

    async def test_releasenotes_tasks_returns_false_if_absent(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=404)

        received = await release_notes('firefox', '52.0.2')
        assert received is False

    async def test_archives_tasks_returns_true_if_folder_existspresent(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)

        received = await archives('firefox', '52.0.2')
        assert received is True

    async def test_archives_tasks_returns_false_if_absent(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=404)

        received = await archives('firefox', '52.0.2')
        assert received is False

    async def test_download_links_tasks_returns_true_if_version_matches(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '52.0.2')
        assert received is True

    async def test_download_links_tasks_returns_true_if_older_version(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '52.0')
        assert received is True

    async def test_download_links_tasks_returns_false_if_newer_version(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await download_links('firefox', '54.0')
        assert received is False

    async def test_download_links_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/firefox/all/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await download_links('firefox', '54.0')
        assert str(excinfo.value) == 'Download page not available  (404)'

    async def test_security_advisories_tasks_returns_true_if_version_matches(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '52.0.2')
        assert received is True

    async def test_security_advisories_tasks_returns_true_if_older_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '52.0')
        assert received is True

    async def test_security_advisories_tasks_returns_false_if_newer_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories('firefox', '54.0')
        assert received is False

    async def test_security_advisories_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await security_advisories('firefox', '54.0')
        assert str(excinfo.value) == 'Security advisories page not available  (404)'

    async def test_product_details_tasks_returns_true_if_present(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=200, body=json.dumps({"releases": {"firefox-52.0": {}}}))

        received = await product_details('firefox', '52.0')
        assert received is True

    async def test_product_details_tasks_returns_false_if_absent(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=200, body=json.dumps({"releases": {"firefox-52.0": {}}}))

        received = await product_details('firefox', '54.0')
        assert received is False

    async def test_product_details_tasks_returns_error_if_error(self):
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await product_details('firefox', '54.0')
        assert str(excinfo.value) == 'Product Details info not available  (404)'

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

        resp = await heartbeat(None)
        assert json.loads(resp.body.decode()) == {
            "archive": False,
            "bedrock": False,
            "product-details": False
        }
