from aiohttp import web
import aiohttp_cors
from .views import home, release, utilities


def get_app(loop=None):
    app = web.Application(loop=loop)

    # Allow Web Application calls.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    cors.add(app.router.add_get('/', home.redirect))  # Redirects to /v1/
    cors.add(app.router.add_get('/v1', home.redirect))  # Redirects to /v1/
    cors.add(app.router.add_get('/contribute.json', utilities.contribute_json))
    cors.add(app.router.add_get('/v1/', home.index))
    cors.add(app.router.add_get('/v1/__api__', utilities.oas_spec))
    cors.add(app.router.add_get('/v1/{product}/{version}/archive', release.archive))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/release-notes',
                                release.bedrock_release_notes))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/security-advisories',
                                release.bedrock_security_advisories))
    cors.add(app.router.add_get('/v1/{product}/{version}/bedrock/download-links',
                                release.bedrock_download_links))
    cors.add(app.router.add_get('/v1/{product}/{version}/product-details',
                                release.product_details))
    return app
