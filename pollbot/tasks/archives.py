from . import get_session, heartbeat_factory


async def archives(product, version):
    with get_session() as session:
        url = 'https://archive.mozilla.org/pub/{}/releases/{}/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404


heartbeat = heartbeat_factory('https://archive.mozilla.org/pub/firefox/releases/')
