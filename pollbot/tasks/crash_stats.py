import datetime
from pollbot.utils import Status, Channel, get_version_channel
from . import get_session, build_task_response, heartbeat_factory

CRASH_STATS_SERVER = "https://crash-stats.mozilla.com/api"


async def get_channel_versions(product, version):
    channel = get_version_channel(version)
    url = '{}/ProductVersions/?active=true&build_type={}&product={}'.format(
        CRASH_STATS_SERVER, channel.value, product)
    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            versions = [h['version'] for h in body['hits'][:5]]
            if version not in versions:
                versions.extend([h['version'] for h in body['hits'] if h['version'] == version])
            return versions


async def uptake(product, version):
    channel = get_version_channel(version)
    start_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = datetime.date.today().strftime('%Y-%m-%d')

    if channel is Channel.BETA:
        versions = ['{}b'.format(version.split('b')[0])]
    else:
        versions = await get_channel_versions(product, version)

    url = ('{}/ADI/?start_date={}&end_date={}&'
           'platforms=Windows&platforms=Linux&platforms=Mac%20OS%20X&'
           'product={}&versions={}')
    url = url.format(CRASH_STATS_SERVER, start_date, end_date, product,
                     '&versions='.join(versions))

    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            if not body['hits']:
                status = Status.ERROR
                message = "No crash-stats ADI info for version {}".format(versions)
            else:
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
                    message = 'Crash-Stats uptake for version {} is {:.2f}% ({:,}/{:,})'.format(
                        version, ratio, version_users, total_users)
            return build_task_response(status, url, message)


heartbeat = heartbeat_factory('{}/'.format(CRASH_STATS_SERVER))
