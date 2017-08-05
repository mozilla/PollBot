import aiohttp


async def release_notes_published(product, version):
    with aiohttp.ClientSession() as session:
        url = 'https://www.mozilla.org/en-US/{}/{}/releasenotes/'.format(product, version)
        async with session.get(url) as resp:
            return resp.status != 404
