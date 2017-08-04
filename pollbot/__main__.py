from aiohttp import web
from .views import home, release


def main():
    app = web.Application()
    app.router.add_get('/', home.redirect)
    app.router.add_get('/v1/', home.index)
    app.router.add_get('/v1/firefox/{version}', release.info)

    web.run_app(app, port=8000)
