import pkg_resources
import sys

import aiohttp

from pollbot import __version__ as pollbot_version


def get_session():
    aiohttp_version = pkg_resources.get_distribution("aiohttp").version
    python_version = '.'.join([str(v) for v in sys.version_info[:3]])
    return aiohttp.ClientSession(headers={
        "User-Agent": "PollBot/{} aiohttp/{} python/{}".format(
            pollbot_version, aiohttp_version, python_version)
    })


def heartbeat_factory(url):
    async def heartbeat():
        with get_session() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return True
                return False
    return heartbeat
