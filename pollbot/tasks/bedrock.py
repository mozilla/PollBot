from pyquery import PyQuery as pq
from pollbot.exceptions import TaskError
from pollbot.utils import build_version_id
from . import get_session, heartbeat_factory


async def release_notes(product, version):
    with get_session() as session:
        url = 'https://www.mozilla.org/en-US/{}/{}/releasenotes/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404


async def security_advisories(product, version):
    with get_session() as session:
        url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/{}/'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Security advisories page not available  ({})'.format(resp.status)
                raise TaskError(msg)
            # Does the content contains the version number?
            body = await resp.text()
            d = pq(body)
            last_release = d("html").attr('data-latest-firefox')
            return build_version_id(last_release) >= build_version_id(version)


async def download_links(product, version):
    with get_session() as session:
        url = 'https://www.mozilla.org/en-US/{}/all/'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Download page not available  ({})'.format(resp.status)
                raise TaskError(msg)
            # Does the content contains the version number?
            body = await resp.text()
            d = pq(body)
            last_release = d("html").attr('data-latest-firefox')
            return build_version_id(last_release) >= build_version_id(version)


heartbeat = heartbeat_factory('https://www.mozilla.org/en-US/firefox/all/')
