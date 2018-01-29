from pollbot.exceptions import TaskError
from pollbot.utils import Channel, get_version_channel, build_version_id, Status
from . import get_session, heartbeat_factory, build_task_response


async def ongoing_versions(product):
    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/firefox_versions.json'
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available (HTTP {})'.format(resp.status)
                raise TaskError(msg, url=url)
            body = await resp.json()
            return {
                "esr": body["FIREFOX_ESR"],
                "release": body["LATEST_FIREFOX_VERSION"],
                "beta": body["LATEST_FIREFOX_DEVEL_VERSION"],
                "nightly": body["FIREFOX_NIGHTLY"],
                "devedition": body["FIREFOX_DEVEDITION"],
            }


async def product_details(product, version):
    if get_version_channel(product, version) is Channel.NIGHTLY:
        versions = await ongoing_versions(product)
        status = build_version_id(versions["nightly"]) >= build_version_id(version)
        message = "Last nightly version is {}".format(versions["nightly"])
        url = "https://product-details.mozilla.org/1.0/{}_versions.json".format(product)
        return build_task_response(status, url, message)

    with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/firefox.json'
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available (HTTP {})'.format(resp.status)
                raise TaskError(msg, url=url)
            body = await resp.json()
            status = 'firefox-{}'.format(version) in body['releases']

            exists_message = "We found product-details information about version {}"
            missing_message = "We did not find product-details information about version {}"
            return build_task_response(status, url,
                                       exists_message.format(version),
                                       missing_message.format(version))


async def devedition_and_beta_in_sync(product, version):
    channel = get_version_channel(product, version)
    url = "https://product-details.mozilla.org/1.0/firefox_versions.json"
    if channel in (Channel.BETA, Channel.AURORA):
        versions = await ongoing_versions(product)
        beta = versions["beta"]
        devedition = versions["devedition"]
        status = beta == devedition
        message = "Last beta version is {} and last devedition is {}".format(beta, devedition)
        return build_task_response(status, url, message)

    # Ignore other channels
    return build_task_response(
        status=Status.MISSING,
        link=url,
        message="No devedition and beta check for '{}' releases".format(channel.value.lower()))


heartbeat = heartbeat_factory('https://product-details.mozilla.org/1.0/firefox.json')
