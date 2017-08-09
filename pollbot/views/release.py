import asyncio
from aiohttp import web
from pollbot import PRODUCTS

from ..exceptions import TaskError
from ..tasks.archives import archives
from ..tasks.bedrock import release_notes, security_advisories, download_links
from ..tasks.product_details import product_details


def get_status(status):
    return status and "exists" or "missing"


async def delivery_dashboard(request):
    product = request.match_info['product']
    version = request.match_info['version']

    if product not in PRODUCTS:
        return web.json_response({
            'status': 404,
            'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
        }, status=404)

    info = await asyncio.gather(archives(product, version),
                                release_notes(product, version),
                                security_advisories(product, version),
                                download_links(product, version),
                                product_details(product, version))

    return web.json_response({
        "archive": get_status(info[0]),
        "release-notes": get_status(info[1]),
        "security-advisories": get_status(info[2]),
        "download-links": get_status(info[3]),
        "product-details": get_status(info[4]),
    })


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
            "status": get_status(status)
        })
    return wrapped


view_archive = status_response(archives)
view_bedrock_release_notes = status_response(release_notes)
view_bedrock_security_advisories = status_response(security_advisories)
view_bedrock_download_links = status_response(download_links)
view_product_details = status_response(product_details)
