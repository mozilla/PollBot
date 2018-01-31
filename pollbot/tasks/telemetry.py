import os
from datetime import date, timedelta
from urllib.parse import urlencode

from pollbot.exceptions import TaskError
from pollbot.utils import Status, Channel, get_version_channel, yesterday
from . import get_session, build_task_response, heartbeat_factory
from .buildhub import get_build_ids_for_version


TELEMETRY_SERVER = "https://sql.telemetry.mozilla.org"
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY")
ATHENA_DATASOURCE_ID = 26


def get_telemetry_auth_header():
    return {"Authorization": "Key {}".format(TELEMETRY_API_KEY)}.copy()


async def put_query(session, query_title, version_name, query, *, query_id=None, run=True):
    # Update query with the last build_id
    if query_id:
        url = "{}/api/queries/{}".format(TELEMETRY_SERVER, query_id)
    else:
        url = "{}/api/queries".format(TELEMETRY_SERVER)

    payload = {
        "name": query_title,
        "schedule": 50000,  # Twice a day
        "schedule_until": (date.today() + timedelta(days=7)).strftime(
            '%Y-%m-%dT%H:%M:%S'),
        "is_draft": True,
        "query": query,
        "data_source_id": ATHENA_DATASOURCE_ID,
        "options": {"parameters": []}
    }
    async with session.post(url, json=payload) as resp:
        if resp.status != 200:
            message = "Unable to create the new query for {} (HTTP {})"
            raise TaskError(message.format(version_name, resp.status), url=url)
        body = await resp.json()
        query_id = body["id"]

    if run:
        # Query for results
        url = "{}/api/query_results".format(TELEMETRY_SERVER)
        payload = {
            "data_source_id": ATHENA_DATASOURCE_ID,
            "query": query,
            "max_age": 0,
            "query_id": query_id
        }
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                message = "Unable to execute the query n°{} for {} (HTTP {})"
                raise TaskError(message.format(query_id, version_name, resp.status),
                                url=url)
    return query_id


async def get_query_info_from_title(session, query_title):
    query_params = urlencode({"include_drafts": "true", "q": query_title})
    query_url = "{}/api/queries/search?{}".format(TELEMETRY_SERVER, query_params)
    async with session.get(query_url) as resp:
        body = await resp.json()

        if body:
            if 'message' in body:
                raise TaskError("STMO: {}".format(body['message']))
            body = [query for query in body if not query['name'].startswith('Copy of')]
            return body[0] if len(body) > 0 else None


async def main_summary_uptake(product, version):
    channel = get_version_channel(product, version)

    with get_session(headers=get_telemetry_auth_header()) as session:
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

        query = """
WITH updated_t AS (
    SELECT COUNT(*) AS updated
    FROM main_summary
    WHERE submission_date_s3 >= '{submission_date}'
      AND app_build_id IN ({build_ids})
      AND normalized_channel = '{channel}'
),
total_t AS (
    SELECT COUNT(*) AS total
    FROM main_summary
    WHERE submission_date_s3 >= '{submission_date}'
      AND normalized_channel = '{channel}'
)
SELECT updated * 1.0 / total as ratio, updated, total
FROM updated_t, total_t
""".format(build_ids=', '.join(["'{}'".format(bid) for bid in build_ids]),
           submission_date=submission_date,
           channel=channel.value.lower())

        query_info = await get_query_info_from_title(session, query_title)

        if query_info:
            if channel is Channel.NIGHTLY:
                # Update the NIGHTLY query with the last build_ids
                await put_query(session, query_title, version_name, query,
                                query_id=query_info['id'], run=False)

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

        query_id = await put_query(session, query_title, version_name, query)
        url = "{}/queries/{}".format(TELEMETRY_SERVER, query_id)
        message = 'Telemetry uptake calculation for version {} is in progress'.format(version_name)
        return build_task_response(Status.INCOMPLETE, url, message)


heartbeat = heartbeat_factory('{}/api/data_sources/1/version'.format(TELEMETRY_SERVER),
                              headers=get_telemetry_auth_header())
