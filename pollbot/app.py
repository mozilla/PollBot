from aiohttp import web
from .views import home, release, utilities


def get_app(loop=None):
    app = web.Application(loop=loop)
    app.router.add_get('/', home.redirect)
    app.router.add_get('/v1/', home.index)
    app.router.add_get('/v1/__api__', utilities.oas_spec)
    app.router.add_get('/v1/{product}/{version}/archive', release.archive)
    app.router.add_get('/v1/{product}/{version}/bedrock/release-notes',
                       release.bedrock_release_notes)
    return app
