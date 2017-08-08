import logging
from aiohttp import web

logger = logging.getLogger(__package__)


def setup_middlewares(app):
    error_middleware = error_pages({404: handle_404,
                                    500: handle_500})
    app.middlewares.append(error_middleware)


def error_pages(overrides):
    async def middleware(app, handler):
        async def middleware_handler(request):
            try:
                response = await handler(request)
                override = overrides.get(response.status)
                if override is None:
                    return response
                else:
                    return await override(request, response)
            except web.HTTPException as ex:
                override = overrides.get(ex.status)
                if override is None:
                    return await handle_any(request, ex)
                else:
                    return await override(request, ex)
            except Exception as ex:
                return await handle_500(request, error=ex)
        return middleware_handler
    return middleware


async def handle_any(request, response):
    return web.json_response({
        "status": response.status,
        "message": response.reason
    }, status=response.status)


async def handle_404(request, response):
    return web.json_response({
        "status": 404,
        "message": "Page '{}' not found".format(request.path)
    }, status=404)


async def handle_500(request, response=None, error=None):
    logger.error(error)
    return web.json_response({
            "status": 503,
            "message": "Service currently unavailable"
        }, status=503)
