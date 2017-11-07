import os.path
from aiohttp import web

HERE = os.path.dirname(__file__)


async def index(request):
    return web.FileResponse(os.path.join(HERE, '../dashboard/index.html'))
