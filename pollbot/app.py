import os.path
import aiohttp_cors
from aiohttp import web
from aiohttp_swagger import setup_swagger

from .middlewares import setup_middlewares
from .views import home, release, utilities


HERE = os.path.dirname(__file__)


def get_app(loop=None):
    app = web.Application(loop=loop)

    # Setup middlewares
    setup_middlewares(app)

    # Allow Web Application calls.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Home
    cors.add(app.router.add_get('/', home.redirect))  # Redirects to /v1/
    cors.add(app.router.add_get('/v1', home.redirect))  # Redirects to /v1/
    cors.add(app.router.add_get('/v1/', home.index))

    # Utilities
    cors.add(app.router.add_get('/contribute.json', utilities.contribute_json))
    cors.add(app.router.add_get('/v1/__api__', utilities.oas_spec))
    cors.add(app.router.add_get('/v1/__version__', utilities.version))

    # Heartbeat
    cors.add(app.router.add_get('/v1/__heartbeat__', utilities.heartbeat))
    cors.add(app.router.add_get('/v1/__lbheartbeat__', utilities.lbheartbeat))

    # Statuses
    cors.add(app.router.add_get('/v1/{product}/{version}/archive', release.archive))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/release-notes',
                                release.bedrock_release_notes))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/security-advisories',
                                release.bedrock_security_advisories))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/download-links',
                                release.bedrock_download_links))
    cors.add(app.router.add_get('/v1/{product}/{version}/product-details',
                                release.product_details))

    # Swagger UI and documentation
    setup_swagger(app,
                  swagger_url="/v1/api/doc",
                  swagger_from_file=os.path.join(HERE, "api.yaml"))

    return app
