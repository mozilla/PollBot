from pollbot.exceptions import TaskError
from pollbot.utils import build_version_id

from . import get_session, heartbeat_factory


async def ship_it_firefox_versions(product, version):
    with get_session() as session:
        url = 'https://ship-it.mozilla.org/json/1.0/{}_versions.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Ship it info not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            last_release = body["LATEST_FIREFOX_VERSION"]
            return build_version_id(last_release) >= build_version_id(version)


heartbeat = heartbeat_factory('https://ship-it.mozilla.org/json/1.0/firefox_versions.json')
