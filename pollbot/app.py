from aiohttp import web
from .views import home, release, utilities


def get_app(loop=None):
    app = web.Application(loop=loop)
    app.router.add_get('/', home.redirect)
    app.router.add_get('/v1/', home.index)
    app.router.add_get('/v1/__api__', utilities.oas_spec)
    app.router.add_get('/v1/firefox/{version}', release.info)
    return app
