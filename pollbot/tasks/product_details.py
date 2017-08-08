from pollbot.exceptions import TaskError

from . import get_session


async def product_details(product, version):
    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            return '{}-{}'.format(product, version) in body['releases']


async def heartbeat():
    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return True
        return False
