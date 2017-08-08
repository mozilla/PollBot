from . import get_session


async def archives(product, version):
    with get_session() as session:
        url = 'https://archive.mozilla.org/pub/{}/releases/{}/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404


async def heartbeat():
    with get_session() as session:
        url = 'https://archive.mozilla.org/pub/firefox/releases/'
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return True
        return False
