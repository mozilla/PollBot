import aiohttp
import asynctest
import pytest

from aioresponses import aioresponses

from pollbot.exceptions import TaskError
from pollbot.tasks.archives import archives_published
from pollbot.tasks.bedrock import release_notes_published, security_advisories_published


class DeliveryTasksTest(asynctest.TestCase):
    async def setUp(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.addCleanup(self.session.close)

        self.mocked = aioresponses()
        self.mocked.start()
        self.addCleanup(self.mocked.stop)

    async def test_releasenotes_tasks_returns_true_if_present(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes_published('firefox', '52.0.2')
        assert received is True

    async def test_releasenotes_tasks_returns_false_if_absent(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=404)

        received = await release_notes_published('firefox', '52.0.2')
        assert received is False

    async def test_archives_tasks_returns_true_if_folder_existspresent(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=200)

        received = await archives_published('firefox', '52.0.2')
        assert received is True

    async def test_archives_tasks_returns_false_if_absent(self):
        url = 'https://archive.mozilla.org/pub/firefox/releases/52.0.2/'
        self.mocked.get(url, status=404)

        received = await archives_published('firefox', '52.0.2')
        assert received is False

    async def test_security_advisory_tasks_returns_true_if_version_matches(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories_published('firefox', '52.0.2')
        assert received is True

    async def test_security_advisory_tasks_returns_true_if_older_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories_published('firefox', '52.0')
        assert received is True

    async def test_security_advisory_tasks_returns_false_if_newer_version(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=200, body='<html data-latest-firefox="52.0.2"></html>')

        received = await security_advisories_published('firefox', '54.0')
        assert received is False

    async def test_security_advisory_tasks_returns_error_if_error(self):
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/'
        self.mocked.get(url, status=404)

        with pytest.raises(TaskError) as excinfo:
            await security_advisories_published('firefox', '54.0')
        assert str(excinfo.value) == 'Security advisories page not available  (404)'
