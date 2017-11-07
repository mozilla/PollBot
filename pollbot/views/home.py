from aiohttp import web

from .. import __version__ as pollbot_version, HTTP_API_VERSION, PRODUCTS


async def redirect(request):
    return web.HTTPFound('/v1/')


async def index(request):
    proto = request.headers.get('X-Forwarded-Proto', 'http')
    host = request.headers['Host']
    return web.json_response({
        "project_name": "pollbot",
        "project_version": pollbot_version,
        "url": "https://github.com/mozilla/PollBot",
        "http_api_version": HTTP_API_VERSION,
        "dashboard": "{}://{}/delivery-dashboard/".format(proto, host),
        "docs": "{}://{}/v1/api/doc/".format(proto, host),
        "products": PRODUCTS
    })
