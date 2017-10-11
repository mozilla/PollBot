import os
from datetime import date, timedelta
from urllib.parse import urlencode

from pollbot.exceptions import TaskError
from pollbot.utils import Status, Channel, get_version_channel, build_version_id
from . import get_session, build_task_response, heartbeat_factory
from .buildhub import get_build_ids_for_version


TELEMETRY_SERVER = "https://sql.telemetry.mozilla.org"
NIGHTLY_BUILD_IDS = {
    "57.0a1": 40223,  # https://sql.telemetry.mozilla.org/queries/40223/source
    "58.0a1": 40790,  # https://sql.telemetry.mozilla.org/queries/40790/source
}
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY")


def get_telemetry_auth_header():
    return {"Authorization": "Key {}".format(TELEMETRY_API_KEY)}.copy()


async def get_query_info_from_title(session, query_title):
    query_params = urlencode({"include_drafts": "true", "q": query_title})
    query_url = "{}/api/queries/search?{}".format(TELEMETRY_SERVER, query_params)
    async with session.get(query_url) as resp:
        body = await resp.json()
        if body:
            body = [query for query in body if not query['name'].startswith('Copy of')]
            return body[0] if len(body) > 0 else None


async def get_last_build_ids_for_nightly_version(session, version):
    if version not in NIGHTLY_BUILD_IDS:
        raise TaskError("Please configure Build IDs query for {}".format(version))

    query_id = NIGHTLY_BUILD_IDS[version]
    url = "{}/api/queries/{}".format(TELEMETRY_SERVER, query_id)
    async with session.get(url) as resp:
        if resp.status != 200:
            raise TaskError("Query {} unavailable (HTTP {})".format(query_id, resp.status),
                            url=url)

        body = await resp.json()
        if not body:
            message = "Couldn't find any build matching."
            raise TaskError(message, url=url)

        latest_query_data_id = body["latest_query_data_id"]
        url = "{}/api/query_results/{}".format(TELEMETRY_SERVER, latest_query_data_id)
        async with session.get(url) as resp:
            if resp.status != 200:
                message = "Query Result {} unavailable (HTTP {})"
                raise TaskError(message.format(latest_query_data_id, resp.status), url=url)

            body = await resp.json()
            rows = body["query_result"]["data"]["rows"]

            if not rows:
                message = "Couldn't find any build matching."
                raise TaskError(message, url=url)

            last_build_id_date = rows[0]["build_id"][:8]
            return [r["build_id"] for r in rows
                    if r["build_id"].startswith(last_build_id_date)]


async def update_parquet_uptake(product, version):
    channel = get_version_channel(version)
    if build_version_id(version) < build_version_id('57.0a1'):
        return build_task_response(Status.MISSING,
                                   "https://bugzilla.mozilla.org/show_bug.cgi?id=1384861",
                                   "Telemetry update-parquet metrics landed in Firefox Quantum")

    with get_session(headers=get_telemetry_auth_header()) as session:
        if channel is Channel.NIGHTLY:
            # Get the build IDs of the lastest days of nightly
            build_ids = await get_last_build_ids_for_nightly_version(session, version)
        else:
            # Get the build IDs for this channel
            build_ids = await get_build_ids_for_version(product, version)

        version_name = "{} ({})".format(version, ", ".join(build_ids))
        query_title = "Uptake {} {} {}"
        query_title = query_title.format(product.title(), channel.value, version_name)

        query = """
WITH updated_t AS (
    SELECT COUNT(*) AS updated
    FROM telemetry_update_parquet
    WHERE payload.reason = 'success'
      AND environment.build.build_id IN ({build_ids})
),
total_t AS (
    SELECT COUNT(*) AS total, payload.target_version
    FROM telemetry_update_parquet
    WHERE payload.reason = 'ready'
      AND payload.target_build_id IN ({build_ids})
      GROUP BY 2
)
SELECT updated * 1.0 / total as ratio, updated, total
FROM updated_t, total_t
""".format(build_ids=', '.join(["'{}'".format(bid) for bid in build_ids]))

        query_info = await get_query_info_from_title(session, query_title)

        if query_info:
            # In that case the query already exists
            latest_query_data_id = query_info["latest_query_data_id"]

            # In case the query processing didn't start, the last_query_data_id can be None.
            if latest_query_data_id is None:
                url = "{}/queries/{}".format(TELEMETRY_SERVER, query_info['id'])
                return build_task_response(Status.INCOMPLETE, url, "Query still processing.")

            # Get the results if we know the query results ID
            url = "{}/api/query_results/{}".format(TELEMETRY_SERVER, latest_query_data_id)
            async with session.get(url) as resp:
                if resp.status != 200:
                    return build_task_response(
                        Status.MISSING, url,
                        "Query Result {} unavailable (HTTP {})".format(latest_query_data_id,
                                                                       resp.status))

                body = await resp.json()
                # If no data are matching the query, we may have an empty list of results,
                if not body["query_result"]["data"]["rows"]:
                    url = "{}/queries/{}".format(TELEMETRY_SERVER, query_info['id'])
                    return build_task_response(Status.ERROR, url,
                                               "No result found for your query.")

                data = body["query_result"]["data"]["rows"][0]

            # version_users = data["updated"]
            # total_users = data["total"]
            ratio = data["ratio"]

            if ratio < 0.5:
                status = Status.INCOMPLETE
            else:
                status = Status.EXISTS
            url = "{}/queries/{}".format(TELEMETRY_SERVER, query_info["id"])
            message = 'Telemetry uptake for version {} is {:.2f}%'.format(
                version_name, ratio * 100)

            return build_task_response(status, url, message)

        # In that case we couldn't find the query, so we need to create it.
        url = "{}/api/queries".format(TELEMETRY_SERVER)
        payload = {
            "name": query_title,
            "schedule": 3600,
            "is_draft": True,
            "query": query,
            "data_source_id": 1,
            "options": {"parameters": []}
        }
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                message = "Unable to create the new query for {} (HTTP {})"
                raise TaskError(message.format(version_name, resp.status), url=url)
            body = await resp.json()
            query_id = body["id"]

        # Query for results
        url = "{}/api/query_results".format(TELEMETRY_SERVER)
        payload = {
            "data_source_id": 1,
            "query": query,
            "max_age": 0,
            "query_id": query_id
        }
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                message = "Unable to execute the query n°{} for {} (HTTP {})"
                raise TaskError(message.format(query_id, version_name, resp.status), url=url)

        url = "{}/queries/{}".format(TELEMETRY_SERVER, query_id)
        message = 'Telemetry uptake calculation for version {} is in progress'.format(version_name)
        return build_task_response(Status.INCOMPLETE, url, message)


heartbeat = heartbeat_factory('{}/api/data_sources/1/version'.format(TELEMETRY_SERVER),
                              headers=get_telemetry_auth_header())
