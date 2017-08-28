from aiohttp import web
from collections import OrderedDict
from pollbot import PRODUCTS

from ..exceptions import TaskError
from ..tasks.archives import archives
from ..tasks.bedrock import release_notes, security_advisories, download_links, get_releases
from ..tasks.product_details import product_details
from ..utils import Channel, get_version_channel


def status_response(task):
    async def wrapped(request):
        product = request.match_info['product']
        version = request.match_info['version']

        if product not in PRODUCTS:
            return web.json_response({
                'status': 404,
                'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
            }, status=404)

        try:
            status = await task(product, version)
        except TaskError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
        return web.json_response({
            "status": status and "exists" or "missing"
        })
    return wrapped


archive = status_response(archives)
bedrock_release_notes = status_response(release_notes)
bedrock_security_advisories = status_response(security_advisories)
bedrock_download_links = status_response(download_links)
product_details = status_response(product_details)


async def view_get_releases(request):
    product = request.match_info['product']

    if product not in PRODUCTS:
        return web.json_response({
            'status': 404,
            'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
        }, status=404)

    return web.json_response({
        "releases": await get_releases(product)
    })


CHECKS_INFO = {
    "archive-date": {"url": "/v1/{product}/{version}/archive-date", "title": "Archive Date"},
    "archive-date-l10n": {"url": "/v1/{product}/{version}/archive-date-l10n",
                          "title": "Archive Date l10n"},
    "archive": {"url": "/v1/{product}/{version}/archive", "title": "Archive Release"},
    "release-notes": {"url": "/v1/{product}/{version}/bedrock/release-notes",
                      "title": "Release notes"},
    "security-advisories": {"url": "/v1/{product}/{version}/bedrock/security-advisories",
                            "title": "Security advisories"},
    "download-links": {"url": "/v1/{product}/{version}/bedrock/download-links",
                       "title": "Download links"},
    "product-details": {"url": "/v1/{product}/{version}/product-details",
                        "title": "Product details"},
}


CHECKS = OrderedDict(
    sorted({
        "archive-date": [Channel.NIGHTLY],
        "archive-date-l10n": [Channel.NIGHTLY],
        "archive": [Channel.ESR, Channel.RELEASE, Channel.BETA],
        "release-notes": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY],
        "security-advisories": [Channel.ESR, Channel.RELEASE],
        "download-links": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY],
        "product-details": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY]
    }.items(), key=lambda t: t[0]))


async def view_get_checks(request):
    product = request.match_info['product']

    if product not in PRODUCTS:
        return web.json_response({
            'status': 404,
            'message': 'Invalid product: {} not in {}'.format(product, PRODUCTS)
        }, status=404)

    version = request.match_info['version']
    channel = get_version_channel(version)

    proto = request.headers.get('X-Forwarded-Proto', 'http')
    host = request.headers['Host']

    checks = []

    for check_name, channels in CHECKS.items():
        if channel in channels:
            info = CHECKS_INFO[check_name].copy()
            info['url'] = ("{}://{}" + info['url']).format(proto, host,
                                                           product=product, version=version)
            checks.append(info)

    return web.json_response({
        "product": product,
        "version": version,
        "channel": channel.value.lower(),
        "checks": checks,
    })
