import logging
from aiohttp import web
from collections import OrderedDict

from ..tasks.archives import archives, archives_date, archives_date_l10n
from ..tasks.bedrock import release_notes, security_advisories, download_links, get_releases
from ..tasks.product_details import product_details, devedition_and_beta_in_sync
from ..utils import Channel, get_version_channel
from .decorators import validate_product_version

logger = logging.getLogger(__package__)


def status_response(task):
    @validate_product_version
    async def wrapped(request, product, version):
        try:
            response = await task(product, version)
        except Exception as e:  # In case something went bad, we return an error status message
            logger.exception(e)
            return web.json_response({
                'status': 'error',
                'message': str(e)
            })
        return web.json_response(response)
    return wrapped


archive = status_response(archives)
archive_date = status_response(archives_date)
archive_date_l10n = status_response(archives_date_l10n)
bedrock_release_notes = status_response(release_notes)
bedrock_security_advisories = status_response(security_advisories)
bedrock_download_links = status_response(download_links)
product_details = status_response(product_details)
devedition_beta_check = status_response(devedition_and_beta_in_sync)


@validate_product_version
async def view_get_releases(request, product):
    return web.json_response({
        "releases": await get_releases(product)
    })


CHECKS_TITLE = {
    "archive-date": "Archive Date",
    "archive-date-l10n": "Archive Date l10n",
    "archive": "Archive Release",
    "release-notes": "Release notes",
    "security-advisories": "Security advisories",
    "download-links": "Download links",
    "product-details": "Product details",
    "devedition-beta-matches": "Devedition and Beta versions matches",
}


CHECKS = OrderedDict(
    sorted({
        "archive-date": [Channel.NIGHTLY],
        "archive-date-l10n": [Channel.NIGHTLY],
        "archive": [Channel.ESR, Channel.RELEASE, Channel.BETA],
        "release-notes": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY],
        "security-advisories": [Channel.ESR, Channel.RELEASE],
        "download-links": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY],
        "product-details": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.NIGHTLY],
        "devedition-beta-matches": [Channel.BETA],
    }.items(), key=lambda t: t[0]))


@validate_product_version
async def view_get_checks(request, product, version):
    channel = get_version_channel(version)

    proto = request.headers.get('X-Forwarded-Proto', 'http')
    host = request.headers['Host']

    checks = []
    router = request.app.router

    for check_name, channels in CHECKS.items():
        if channel in channels:
            prefix = "{}://{}".format(proto, host)
            url = router[check_name].url_for(product=product, version=version)
            info = {
                "title": CHECKS_TITLE[check_name],
                "url": "{}{}".format(prefix, url)
            }
            checks.append(info)

    return web.json_response({
        "product": product,
        "version": version,
        "channel": channel.value.lower(),
        "checks": checks,
    })
