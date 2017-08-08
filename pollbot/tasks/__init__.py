import pkg_resources
import sys

import aiohttp

from pollbot import __version__ as pollbot_version


# Module version, as defined in PEP-0396.


def get_session():
    aiohttp_version = pkg_resources.get_distribution("aiohttp").version
    python_version = '.'.join(map(str, sys.version_info[:3]))
    return aiohttp.ClientSession(headers={
        "User-Agent": "PollBot/{} aiohttp/{} python/{}".format(
            pollbot_version, aiohttp_version, python_version)
    })
