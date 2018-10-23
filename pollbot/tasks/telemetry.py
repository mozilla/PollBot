import os
from datetime import date, timedelta
from urllib.parse import urlencode

from pollbot.exceptions import TaskError
from pollbot.utils import Status, Channel, get_version_channel, yesterday
from . import get_session, build_task_response, heartbeat_factory
from .buildhub import get_build_ids_for_version


TELEMETRY_SERVER = "https://sql.telemetry.mozilla.org"
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY")
# TELEMETRY_USER_ID = os.getenv("TELEMETRY_USER_ID")
TELEMETRY_UPTAKE_QUERY_ID = int(os.getenv(
    "POLLBOT_TELEMETRY_UPTAKE_QUERY_ID",  59383)
)
# ATHENA_DATASOURCE_ID = 26
# https://docs.telemetry.mozilla.org/datasets/batch_view/main_summary/reference.html \
#    #background-and-caveats
# TELEMETRY_CACHED_SAMPLE = 42


class TelemetryUptakeConfigurationError(Exception):
    """When there's something wrong with reaching the Telemetry Uptake query"""


def get_telemetry_auth_header():
    return {"Authorization": "Key {}".format(TELEMETRY_API_KEY)}.copy()


async def get_query_info_from_title(session, query_title):
    query_params = urlencode({"include_drafts": "true", "q": query_title})
    query_url = "{}/api/queries/search?{}".format(TELEMETRY_SERVER, query_params)
    async with session.get(query_url) as resp:
        body = await resp.json()

        if body:
            if 'message' in body:
                raise TaskError("STMO: {}".format(body['message']))
            body = [query for query in body['results']
                    if not query['name'].startswith('Copy of') and
                    query['user']['id'] == int(TELEMETRY_USER_ID)]
            return body[0] if len(body) > 0 else None


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
        message = 'Telemetry uptake for version {} is {:.1f}%'.format(
            version_name, ratio * 100)

        return build_task_response(status, url, message)


heartbeat = heartbeat_factory('{}/api/data_sources/1/version'.format(TELEMETRY_SERVER),
                              headers=get_telemetry_auth_header())
