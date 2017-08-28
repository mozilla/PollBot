from pollbot.exceptions import TaskError
from pollbot.utils import Channel, get_version_channel, build_version_id
from . import get_session, heartbeat_factory


async def ongoing_versions(product):
    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}_versions.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            return {
                "esr": body["FIREFOX_ESR"],
                "release": body["LATEST_FIREFOX_VERSION"],
                "beta": body["LATEST_FIREFOX_DEVEL_VERSION"],
                "nightly": body["FIREFOX_NIGHTLY"],
            }


async def product_details(product, version):
    if get_version_channel(version) is Channel.NIGHTLY:
        versions = await ongoing_versions(product)
        status = build_version_id(versions["nightly"]) >= build_version_id(version)
        return {
            "status":  status and "exists" or "missing",
            "message": "Checking product-details for the nightly version",
            "link": 'https://product-details.mozilla.org/1.0/{}_versions.json'.format(product)
        }

    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            status = '{}-{}'.format(product, version) in body['releases']
            return {
                "status":  status and "exists" or "missing",
                "message": "Checking product-details for the release version",
                "link": url
            }


heartbeat = heartbeat_factory('https://product-details.mozilla.org/1.0/firefox.json')
