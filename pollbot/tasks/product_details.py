import aiohttp
from pollbot.exceptions import TaskError


async def product_details(product, version):
    with aiohttp.ClientSession() as session:
        url = 'https://product-details.mozilla.org/1.0/{}.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            return '{}-{}'.format(product, version) in body['releases']
