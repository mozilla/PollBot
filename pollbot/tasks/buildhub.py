from urllib.parse import urlencode

from pollbot.utils import Channel, get_version_channel

from . import get_session, build_task_response, heartbeat_factory


BUILDHUB_SERVER = "https://buildhub.stage.mozaws.net/v1"


async def buildhub(product, version):
    params = {
        "source.product": product,
        "target.version": '"%s"' % version,
        "has_build.id": "true",
        "_limit": 1,
    }
    missing_message = 'Buildhub does not contain any information about this release yet.'

    channel = get_version_channel(version)
    if channel is Channel.NIGHTLY:
        params.update({
            "_sort": "-build.id",
        })
        exists_message = 'Latest Nightly build id is {record[build][id]} for this version.'

    else:
        exists_message = 'Build id is {record[build][id]} for this release.'

    url = '{}/buckets/build-hub/collections/releases/records?{}'
    url = url.format(BUILDHUB_SERVER, urlencode(params))

    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            status = len(body['data']) > 0

            if status:
                record = body['data'][0]
                exists_message = exists_message.format(record=record)

            url = "https://mozilla-services.github.io/buildhub/?versions[0]={}&products[0]={}"
            url = url.format(version, product)
            return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('{}/__heartbeat__'.format(BUILDHUB_SERVER))
