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

    info = await ongoing_versions(product)
    info = {k: v for k, v in info.items() if (product == "devedition") == (k == "devedition")}

    return web.json_response(info)
