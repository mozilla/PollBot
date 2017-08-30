from pollbot.exceptions import TaskError
from pollbot.utils import Channel, get_version_channel, build_version_id
from . import get_session, heartbeat_factory, build_task_response


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
        message = "Last nightly version is {}".format(versions["nightly"])
        url = "https://product-details.mozilla.org/1.0/{}_versions.json".format(product)
        return build_task_response(status, url, message)

    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}.json'.format(product)
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available (HTTP {})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.json()
            status = '{}-{}'.format(product, version) in body['releases']

            exists_message = "We found product-details information about version {}".format(
                version)
            missing_message = "We did not found product-details information about version".format(
                version)
            return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('https://product-details.mozilla.org/1.0/firefox.json')
