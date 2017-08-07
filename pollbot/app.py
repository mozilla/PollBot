import os.path
from aiohttp import web
from aiohttp_swagger import setup_swagger
from .views import home, release, utilities


HERE = os.path.dirname(__file__)


def get_app(loop=None):
    app = web.Application(loop=loop)
    app.router.add_get('/', home.redirect)  # Redirects to /v1/
    app.router.add_get('/v1', home.redirect)  # Redirects to /v1/
    app.router.add_get('/contribute.json', utilities.contribute_json)
    app.router.add_get('/v1/', home.index)
    app.router.add_get('/v1/__api__', utilities.oas_spec)
    app.router.add_get('/v1/{product}/{version}/archive', release.archive)
    app.router.add_get('/v1/{product}/{version}/bedrock/release-notes',
                       release.bedrock_release_notes)
    app.router.add_get('/v1/{product}/{version}/bedrock/security-advisories',
                       release.bedrock_security_advisories)
    app.router.add_get('/v1/{product}/{version}/bedrock/download-links',
                       release.bedrock_download_links)
    app.router.add_get('/v1/{product}/{version}/product-details',
                       release.product_details)

    setup_swagger(app,
                  swagger_url="/v1/api/doc",
                  swagger_from_file=os.path.join(HERE, "api.yaml"))
    return app
