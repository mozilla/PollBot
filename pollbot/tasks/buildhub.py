import json

from pollbot.exceptions import TaskError
from pollbot.utils import (
    Channel, Status, get_version_channel, yesterday, strip_candidate_info
)

from . import get_session, build_task_response, heartbeat_factory


BUILDHUB_SERVER = "https://buildhub.prod.mozaws.net/v1"

RELEASE_CHANNEL = {
    'devedition': 'aurora',
    'firefox': 'release',
}


async def get_releases(product, version=None, *, max_releases=1000):
    if version is None:
        channel = RELEASE_CHANNEL[product]
    else:
        channel = get_version_channel(product, version).value.lower()

    query = {
        "aggs": {
            "by_build_id": {
                "aggs": {
                    "versions": {
                        "terms": {
                            "field": "target.version"
                        }
                    }
                },
                "terms": {
                    "field": "build.id",
                    "size": max_releases,
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
                            "source.product": product
                        }
                    }, {
                        "term": {
                            "target.channel": channel
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
            if response.status != 200:
                message = "Buildhub is not available ({})".format(response.status)
                url = "https://mozilla-services.github.io/buildhub/?products[0]={}".format(product)
                raise TaskError(message, url=url)

            data = await response.json()
        versions = []
        for build_id_bucket in data['aggregations']['by_build_id']['buckets']:
            version_build_id = build_id_bucket["key"]
            version = [r["key"] for r in build_id_bucket["versions"]["buckets"]
                       if strip_candidate_info(r['key']) == r['key']]
            if version:
                versions.append((version_build_id, version[0]))

        if not versions:
            message = "Couldn't find any version matching."
            url = "https://mozilla-services.github.io/buildhub/?products[0]={}".format(product)
            raise TaskError(message, url=url)

        return versions


def get_buildhub_url(product, version, channel):
    channel_value = channel.value.lower()
    if product == "devedition":
        channel_value = "aurora"

    url = ("https://mozilla-services.github.io/buildhub/"
           "?versions[0]={}&products[0]={}&channel[0]={}")
    return url.format(version, product, channel_value)


async def get_build_ids_for_version(product, version, *, size=10):
    channel = get_version_channel(product, strip_candidate_info(version))
    channel_value = channel.value.lower()
    if product == "devedition":
        channel_value = "aurora"

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
                            "target.channel": channel_value
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
            raise TaskError(message, url=get_buildhub_url(product, version, channel))

        return build_ids


async def buildhub(product, version):
    if 'build' in version:
        version = version.replace('build', 'rc')

    try:
        build_ids = await get_build_ids_for_version(product, version)
        status = True
    except TaskError:
        status = False

    channel = get_version_channel(product, strip_candidate_info(version))
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

    url = get_buildhub_url(product, version, channel)
    return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('{}/__heartbeat__'.format(BUILDHUB_SERVER))
