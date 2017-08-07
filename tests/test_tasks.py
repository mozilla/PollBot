import aiohttp
import asynctest
from aioresponses import aioresponses

from pollbot.tasks.releasenotes import release_notes_published
from pollbot.tasks.archives import archives_published


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
