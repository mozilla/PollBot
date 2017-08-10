from aiohttp import web
from pollbot import PRODUCTS

from ..tasks.product_details import ongoing_versions


async def get_ongoing_versions(request):
    product = request.match_info['product']

    if product not in PRODUCTS:
        return web.json_response({
            'status': 404,
            'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
        }, status=404)

    return web.json_response(await ongoing_versions(product))
