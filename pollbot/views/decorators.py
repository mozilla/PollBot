from aiohttp import web

from pollbot import PRODUCTS
from ..utils import is_valid_version, Channel, get_version_channel


def validate_product_version(func):
    async def decorate(request):
        product = request.match_info['product']
        version = request.match_info.get('version')

        if product not in PRODUCTS:
            return web.json_response({
                'status': 404,
                'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
            }, status=404)

        if version and not is_valid_version(version):
            return web.json_response({
                'status': 404,
                'message': 'Invalid version number: {}'.format(version)
            }, status=404)

        if version:
            if product == "devedition":
                channel = get_version_channel(product, version)
                if channel is not Channel.AURORA:
                    return web.json_response({
                        'status': 404,
                        'message': 'Invalid version number for devedition: {}'.format(version)
                    }, status=404)

            return await func(request, product, version)

        return await func(request, product)

    return decorate
