import aiohttp
import asynctest
from aioresponses import aioresponses

from pollbot.tasks.releasenotes import release_notes_published


class ReleasePublishedTest(asynctest.TestCase):
    url = 'http://test.example.com'
    data = {'foo': 'bar'}

    async def setUp(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.addCleanup(self.session.close)

        self.mocked = aioresponses()
        self.mocked.start()
        self.addCleanup(self.mocked.stop)

    async def test_returns_true_if_present(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=200)

        received = await release_notes_published('firefox', '52.0.2')
        assert received is True

    async def test_returns_false_if_absent(self):
        url = 'https://www.mozilla.org/en-US/firefox/52.0.2/releasenotes/'
        self.mocked.get(url, status=404)

        received = await release_notes_published('firefox', '52.0.2')
        assert received is False
