from aiohttp import web
from pollbot import PRODUCTS

from ..exceptions import TaskError
from ..tasks.archives import archives_published
from ..tasks.bedrock import release_notes_published, security_advisories_published


def status_response(task):
    async def wrapped(request):
        product = request.match_info['product']
        version = request.match_info['version']

        if product not in PRODUCTS:
            return web.json_response({
                'status': 404,
                'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
            }, status=404)

        try:
            status = await task(product, version)
        except TaskError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
        return web.json_response({
            "status": status and "exists" or "missing"
        })
    return wrapped


archive = status_response(archives_published)
bedrock_release_notes = status_response(release_notes_published)
bedrock_security_advisories = status_response(security_advisories_published)
