from aiohttp import web
from pollbot import PRODUCTS

from ..tasks.releasenotes import release_notes_published
from ..tasks.archives import archives_published


def status_response(task):
    async def wrapped(request):
        product = request.match_info['product']
        version = request.match_info['version']

        if product not in PRODUCTS:
            return web.json_response({
                'status': 404,
                'error': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
            }, status=404)

        status = await task(product, version)
        return web.json_response({
            "status": status and "exists" or "missing"
        })
    return wrapped


archive = status_response(archives_published)
bedrock_release_notes = status_response(release_notes_published)
