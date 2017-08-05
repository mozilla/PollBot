import aiohttp


async def archives_published(product, version):
    with aiohttp.ClientSession() as session:
        url = 'https://archive.mozilla.org/pub/{}/releases/{}/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404
