import json

from pollbot.exceptions import TaskError
from pollbot.utils import Channel, Status, get_version_channel, yesterday

from . import get_session, build_task_response, heartbeat_factory


BUILDHUB_SERVER = "https://buildhub.stage.mozaws.net/v1"


async def get_build_ids_for_version(product, version, *, size=10):
    channel = get_version_channel(version)
    query = {
        "aggs": {
            "by_version": {
                "terms": {
                    "field": "build.id",
                    "size": size,
                    "order": {
                        "_term": "desc"
                    }
                }
            }
        },
        "query": {
            "bool": {
                "filter": [
                    {
                        "term": {
                            "target.channel": channel.value.lower()
                        }
                    }, {
                        "term": {
                            "source.product": product
                        }
                    }, {
                        "term": {
                            "target.version": version
                        }
                    }
                ]
            }
        },
        "size": 0
    }
    with get_session() as session:
        url = '{}/buckets/build-hub/collections/releases/search'
        url = url.format(BUILDHUB_SERVER)
        async with session.post(url, data=json.dumps(query)) as response:
            data = await response.json()
        build_ids = [r['key'] for r in data['aggregations']['by_version']['buckets']]

        if not build_ids:
            message = "Couldn't find any build matching."
            raise TaskError(message, url=url)

        return build_ids


async def buildhub(product, version):
    try:
        build_ids = await get_build_ids_for_version(product, version)
        status = True
    except TaskError:
        status = False

    channel = get_version_channel(version)
    exists_message = 'Build IDs for this release: {}'
    missing_message = 'Buildhub does not contain any information about this release yet.'

    if status:
        if channel is Channel.NIGHTLY:
            last_expected_nightly = yesterday(formating='%Y%m%d')
            if build_ids[0][:8] < last_expected_nightly:
                status = Status.INCOMPLETE
                build_ids = build_ids[:3]
            else:
                build_ids = [bid for bid in build_ids if bid > last_expected_nightly]

        exists_message = exists_message.format(', '.join(build_ids))

    url = ("https://mozilla-services.github.io/buildhub/"
           "?versions[0]={}&products[0]={}&channel[0]={}")
    url = url.format(version, product, channel.value.lower())
    return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('{}/__heartbeat__'.format(BUILDHUB_SERVER))
