import logging
from aiohttp import web
from collections import OrderedDict

from ..tasks import balrog, buildhub, crash_stats, telemetry
from ..tasks.archives import archives, partner_repacks
from ..tasks.bedrock import release_notes, security_advisories, download_links
from ..tasks.bouncer import bouncer
from ..tasks.buildhub import get_releases
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
            body = {
                'status': 'error',
                'message': str(e)
            }
            if hasattr(e, 'url') and e.url is not None:
                body['link'] = e.url

            return web.json_response(body)
        return web.json_response(response)
    return wrapped


archive = status_response(archives)
partner_repacks = status_response(partner_repacks)
bedrock_release_notes = status_response(release_notes)
bedrock_security_advisories = status_response(security_advisories)
bedrock_download_links = status_response(download_links)
bouncer_download_links = status_response(bouncer)
product_details = status_response(product_details)
devedition_beta_check = status_response(devedition_and_beta_in_sync)
balrog_rules = status_response(balrog.balrog_rules)
buildhub_check = status_response(buildhub.buildhub)
crash_stats_uptake = status_response(crash_stats.uptake)
telemetry_uptake = status_response(telemetry.main_summary_uptake)


@validate_product_version
async def view_get_releases(request, product):
    return web.json_response({
        "releases": await get_releases(product)
    })


CHECKS_TITLE = {
    "archive": "Archive Release",
    "partner-repacks": "Partner repacks",
    "release-notes": "Release notes",
    "security-advisories": "Security advisories",
    "download-links": "Download links",
    "bouncer": "Bouncer",
    "product-details": "Product details",
    "devedition-beta-matches": "Devedition and Beta versions matches",
    "balrog-rules": "Balrog update rules",
    "buildhub": "Buildhub release info",
    "crash-stats-uptake": "Crash Stats Uptake (24h latency)",
    "telemetry-main-summary-uptake": "Telemetry Main Summary Uptake (24h latency)",
}

ALL = [Channel.ESR, Channel.RELEASE, Channel.CANDIDATE,
       Channel.BETA, Channel.AURORA, Channel.NIGHTLY]

CHECKS = OrderedDict(
    sorted({
        "archive": ALL,
        "partner-repacks": [Channel.RELEASE, Channel.BETA, Channel.AURORA, Channel.CANDIDATE],
        "release-notes": [Channel.ESR, Channel.RELEASE, Channel.BETA,
                          Channel.AURORA, Channel.NIGHTLY],
        "security-advisories": [Channel.ESR, Channel.RELEASE],
        "download-links": [Channel.ESR, Channel.RELEASE, Channel.BETA,
                           Channel.AURORA, Channel.NIGHTLY],
        "product-details": [Channel.ESR, Channel.RELEASE, Channel.BETA,
                            Channel.AURORA, Channel.NIGHTLY],
        "devedition-beta-matches": [Channel.BETA, Channel.AURORA],
        "balrog-rules": [Channel.ESR, Channel.RELEASE, Channel.BETA,
                         Channel.AURORA, Channel.NIGHTLY],
        "bouncer": [Channel.ESR, Channel.RELEASE, Channel.BETA, Channel.AURORA, Channel.NIGHTLY],
        "buildhub": ALL,
        "crash-stats-uptake": [Channel.ESR, Channel.RELEASE, Channel.BETA],
        "telemetry-main-summary-uptake": [Channel.ESR, Channel.RELEASE, Channel.BETA,
                                          Channel.AURORA, Channel.NIGHTLY],
    }.items(), key=lambda t: t[0]))

NOT_ACTIONABLE = ['-uptake']
IGNORES = {'devedition': ['crash-stats-uptake', 'partner-repacks']}


@validate_product_version
async def view_get_checks(request, product, version):
    channel = get_version_channel(product, version)

    proto = request.headers.get('X-Forwarded-Proto', 'http')
    host = request.headers['Host']

    checks = []
    router = request.app.router

    for check_name, channels in CHECKS.items():
        check_related_to_version = False
        if channel in channels:
            # List of related channels
            check_related_to_version = True

        if product in IGNORES:
            if check_name in IGNORES[product]:
                check_related_to_version = False

        if check_related_to_version:
            prefix = "{}://{}".format(proto, host)
            url = router[check_name].url_for(product=product, version=version)
            info = {
                "title": CHECKS_TITLE[check_name],
                "url": "{}{}".format(prefix, url),
                "actionable": all([na not in check_name for na in NOT_ACTIONABLE])
            }
            checks.append(info)

    return web.json_response({
        "product": product,
        "version": version,
        "channel": channel.value.lower(),
        "checks": sorted(checks, key=lambda check: check['actionable'], reverse=True),
    })
