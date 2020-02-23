from pollbot.exceptions import TaskError
from pollbot.utils import Channel, get_version_channel, build_version_id, Status
from . import get_session, heartbeat_factory, build_task_response

_product_details = {
    "thunderbird": {
        "versions_url": "thunderbird_versions.json",
        "releases_url": "thunderbird.json",
        "ongoing_versions": {
            "release": "LATEST_THUNDERBIRD_VERSION",
            "beta": "LATEST_THUNDERBIRD_DEVEL_VERSION",
            "nightly": "LATEST_THUNDERBIRD_NIGHTLY_VERSION"
        },
    },
    "firefox": {
        "versions_url": "firefox_versions.json",
        "releases_url": "firefox.json",
        "ongoing_versions": {
            "esr": "FIREFOX_ESR",
            "release": "LATEST_FIREFOX_VERSION",
            "beta": "LATEST_FIREFOX_DEVEL_VERSION",
            "nightly": "FIREFOX_NIGHTLY",
            "devedition": "FIREFOX_DEVEDITION",
        },
    },
    "devedition": {
        "versions_url": "firefox_versions.json",
        "releases_url": "firefox.json",
        "ongoing_versions": {
            "devedition": "FIREFOX_DEVEDITION",
        },
    },
}


def details_versions_url(product):
    return _product_details[product]['versions_url']


def details_releases_url(product):
    return _product_details[product]['releases_url']


def details_ongoing_versions(product, body):
    rv = {}
    for channel, version_key in _product_details[product]['ongoing_versions'].items():
        rv[channel] = body.get(version_key)
    return rv


async def ongoing_versions(product):
    async with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}'.format(details_versions_url(product))
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available (HTTP {})'.format(resp.status)
                raise TaskError(msg, url=url)
            body = await resp.json()
            return details_ongoing_versions(product, body)


async def product_details(product, version):
    if get_version_channel(product, version) is Channel.NIGHTLY:
        versions = await ongoing_versions(product)
        status = build_version_id(versions["nightly"]) >= build_version_id(version)
        message = "Last nightly version is {}".format(versions["nightly"])
        url = "https://product-details.mozilla.org/1.0/{}".format(details_versions_url(product))
        return build_task_response(status, url, message)

    async with get_session() as session:
        url = 'https://product-details.mozilla.org/1.0/{}'.format(details_releases_url(product))
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Product Details info not available (HTTP {})'.format(resp.status)
                raise TaskError(msg, url=url)
            body = await resp.json()
            details_product = 'firefox' if product == 'devedition' else product
            status = '{}-{}'.format(details_product, version) in body['releases']

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
