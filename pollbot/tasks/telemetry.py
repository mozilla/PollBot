import os

from pollbot.utils import Status, Channel, get_version_channel, yesterday
from . import get_session, build_task_response, heartbeat_factory
from .buildhub import get_build_ids_for_version


TELEMETRY_SERVER = "https://sql.telemetry.mozilla.org"
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY")
TELEMETRY_UPTAKE_QUERY_ID = int(os.getenv(
    "POLLBOT_TELEMETRY_UPTAKE_QUERY_ID",  59383)
)


class TelemetryUptakeConfigurationError(Exception):
    """When there's something wrong with reaching the Telemetry Uptake query"""


def get_telemetry_auth_header():
    return {"Authorization": "Key {}".format(TELEMETRY_API_KEY)}.copy()


async def get_saved_query_by_id(session, query_id):
    url = "{}/api/queries/{}".format(TELEMETRY_SERVER, query_id)
    async with session.get(url) as resp:
        if resp.status == 200:
            body = await resp.json()
            return body


async def get_query_results(session, query_data_id):
    url = "{}/api/query_results/{}".format(TELEMETRY_SERVER, query_data_id)
    async with session.get(url) as resp:
        if resp.status == 200:
            body = await resp.json()
            return body['query_result']


async def main_summary_uptake(product, version):
    channel = get_version_channel(product, version)

    async with get_session(headers=get_telemetry_auth_header()) as session:
        # Get the build IDs for this channel
        build_ids = await get_build_ids_for_version(product, version)

        submission_date = yesterday(formating='%Y%m%d')
        if channel is Channel.NIGHTLY:
            build_ids = [bid for bid in build_ids if bid > submission_date]
            version_name = "{} ({})".format(version, ", ".join(build_ids))
            query_title = "Uptake {} {}"
            query_title = query_title.format(product.title(), channel.value)
        else:
            version_name = "{} ({})".format(version, ", ".join(build_ids))
            query_title = "Uptake {} {} {}"
            query_title = query_title.format(product.title(), channel.value, version_name)

        url = "https://sql.telemetry.mozilla.org/queries/{}".format(TELEMETRY_UPTAKE_QUERY_ID)

        saved_query = await get_saved_query_by_id(session, TELEMETRY_UPTAKE_QUERY_ID)
        if not saved_query:
            raise TelemetryUptakeConfigurationError(
                "The saved Telemetry Uptake query can't be found. "
                "({})".format(url)
            )

        query_data_id = saved_query["latest_query_data_id"]
        query_results = await get_query_results(session, query_data_id)

        rows = query_results["data"]["rows"]
        if not rows:
            return build_task_response(Status.ERROR, url,
                                       "Query results contained no rows.")

        # Looking up on a set is much faster.
        our_build_ids = set(build_ids)
        our_normalized_channel = channel.value.lower()
        updated = 0
        total = None
        for row in rows:
            if row['normalized_channel'] != our_normalized_channel:
                continue

            total = row['total']
            if row['app_build_id'] in our_build_ids:
                updated += row['updated']

        if total:
            ratio = updated / total
        else:
            ratio = 0

        if ratio < 0.5:
            status = Status.INCOMPLETE
        else:
            status = Status.EXISTS
        message = 'Telemetry uptake for version {} is {:.3f}%'.format(
            version_name, ratio * 100)

        return build_task_response(status, url, message)


heartbeat = heartbeat_factory('{}/api/data_sources/1/version'.format(TELEMETRY_SERVER),
                              headers=get_telemetry_auth_header())
