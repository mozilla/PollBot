from urllib.parse import urlencode, quote
from pollbot.utils import Status, Channel, get_version_channel, yesterday
from . import get_session, build_task_response, heartbeat_factory

CRASH_STATS_SERVER = "https://crash-stats.mozilla.com/api"


async def get_channel_versions(product, version):
    channel = get_version_channel(product, version)
    url = '{}/ProductVersions/?active=true&build_type={}&product={}'.format(
        CRASH_STATS_SERVER, channel.value, product)
    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            versions = [h['version'] for h in body['hits'][:15]]
            if version not in versions:
                versions.extend([h['version'] for h in body['hits'] if h['version'] == version])
            return versions


def crash_stats_query_url(params):
    params.extend([("platforms", "Windows"),
                   ("platforms", "Linux"),
                   ("platforms", "Mac OS X")])
    return '{}/ADI/?{}'.format(CRASH_STATS_SERVER, urlencode(params, quote_via=quote))


async def uptake(product, version):
    channel = get_version_channel(product, version)
    date = yesterday()

    if channel in (Channel.BETA, Channel.AURORA):
        current_version = version.split('b')[0]
        previous_version = int(version.split('.')[0]) - 1
        versions = ['{}b'.format(current_version), '{}.0b'.format(previous_version)]
    else:
        versions = await get_channel_versions(product, version)

    version_params = [("versions", x) for x in versions]
    params = [("start_date", date),
              ("end_date", date),
              ("product", product)]
    params.extend(version_params)
    url = crash_stats_query_url(params)

    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            if not body['hits']:
                # Try the day before
                date = yesterday(days=2)

                params = [("start_date", date),
                          ("end_date", date),
                          ("product", product)]
                params.extend(version_params)
                url = crash_stats_query_url(params)

                async with session.get(url) as resp:
                    body = await resp.json()
                    if not body['hits']:
                        status = Status.ERROR
                        message = "No crash-stats ADI info for version {}".format(versions)
                        return build_task_response(status, url, message)

            current_version_hits = [h for h in body['hits'] if h['version'] == version]
            if not current_version_hits:
                status = Status.MISSING
                message = "No crash-stats ADI hits for version {}".format(version)
            else:
                version_users = current_version_hits.pop()["adi_count"]
                total_users = sum([h['adi_count'] for h in body['hits']])
                ratio = version_users / total_users
                if ratio < 0.5:
                    status = Status.INCOMPLETE
                else:
                    status = Status.EXISTS
                message = 'Crash-Stats uptake for version {} is {:.2f}%'.format(
                    version, ratio * 100)
        return build_task_response(status, url, message)


heartbeat = heartbeat_factory('https://crash-stats.mozilla.com/monitoring/healthcheck/')
