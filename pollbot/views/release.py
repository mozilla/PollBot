from aiohttp import web


async def info(request):
    release_version = request.match_info['version']
    return web.json_response({
        "product": "firefox",
        "version": release_version
    })
