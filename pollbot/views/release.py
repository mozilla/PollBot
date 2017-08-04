import asyncio
from aiohttp import web
from pollbot.tasks.releasenotes import release_notes_published


async def info(request):
    product = 'firefox'
    version = request.match_info['version']

    infos = await asyncio.gather(release_notes_published(product, version))

    return web.json_response({
        "product": product,
        "version": version,
        "releasenotes": infos[0]
    })
