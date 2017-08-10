import re

from pyquery import PyQuery as pq
from pollbot.exceptions import TaskError
from pollbot.utils import build_version_id
from . import get_session, heartbeat_factory


async def get_releases(product):
    with get_session() as session:
        url = 'https://www.mozilla.org/en-US/{}/releases/'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Releases page not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.text()
            d = pq(body)
            major_releases = [n.text for n in d("strong>a")]
            minor_releases = [n.text for n in d("ol>li>ol>li>a")]
            return sorted(major_releases + minor_releases, key=build_version_id)


async def release_notes(product, version):
    with get_session() as session:
        version = re.sub('esr$', '', version)
        url = 'https://www.mozilla.org/en-US/{}/{}/releasenotes/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404


async def security_advisories(product, version):
    url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/{}/'.format(product)
    return await check_bedrock(url, "Security advisories", version)


async def download_links(product, version):
    url = 'https://www.mozilla.org/en-US/{}/all/'.format(product)
    return await check_bedrock(url, "Download", version)


async def check_bedrock(url, title, version):
    with get_session() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = '{} page not available  ({})'.format(title, resp.status)
                raise TaskError(msg)
            # Does the content contains the version number?
            body = await resp.text()
            d = pq(body)
            if version.endswith('esr'):
                version = re.sub('esr$', '', version)
                last_release = d("html").attr('data-esr-versions')
            else:
                last_release = d("html").attr('data-latest-firefox')
            return build_version_id(last_release) >= build_version_id(version)


heartbeat = heartbeat_factory('https://www.mozilla.org/en-US/firefox/all/')
