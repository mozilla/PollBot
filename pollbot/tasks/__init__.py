import pkg_resources
import sys

import aiohttp

from pollbot import __version__ as pollbot_version
from pollbot.utils import Status


def get_session(*, headers=None):
    aiohttp_version = pkg_resources.get_distribution("aiohttp").version
    python_version = '.'.join([str(v) for v in sys.version_info[:3]])

    session_headers = {
        "User-Agent": "PollBot/{} aiohttp/{} python/{}".format(
            pollbot_version, aiohttp_version, python_version)
    }

    if headers is not None:
        session_headers.update(headers)

    return aiohttp.ClientSession(headers=session_headers)


def heartbeat_factory(url, headers=None):
    async def heartbeat():
        with get_session() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return True
                return False
    return heartbeat


def build_task_response(status, link, message, fail_message=None):
    if fail_message is None:
        fail_message = message

    if isinstance(status, bool):
        message = message if status else fail_message
        status = Status.EXISTS if status else Status.MISSING

    return {
        "status": status.value,
        "message": message,
        "link": link
    }
