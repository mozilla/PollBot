import re

from pollbot.exceptions import TaskError
from pollbot.utils import Channel, Status, get_version_channel, build_version_id
from . import get_session, build_task_response, heartbeat_factory


async def get_release_info(release_mapping):
    release_url = 'https://aus-api.mozilla.org/api/v1/releases/{}'.format(release_mapping)
    with get_session() as session:
            async with session.get(release_url) as resp:
                body = await resp.json()
                platforms = body['platforms']
                built_platforms = [x for x in platforms.keys() if 'locales' in platforms[x]]
                if not built_platforms:
                    raise TaskError('No platform with locales were found in {}'.format(
                        sorted(platforms.keys())), url=release_url)

                build_ids = {}
                appVersions = set()

                for platform in built_platforms:
                    platform_info = platforms[platform]['locales']["de"]
                    build_ids[platform] = platform_info['buildID']
                    appVersions.add(platform_info['displayVersion'].replace(' Beta ', 'b'))
                return build_ids, appVersions


async def balrog_rules(product, version):
    channel = get_version_channel(product, version)
    if channel is Channel.NIGHTLY:
        # In that case the rule doesn't change, so we grab the build IDs.

        # There are case were Nightly is deactivated, in that case
        # the mapping is not nightly-latest anymore
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-nightly'
        with get_session() as session:
            async with session.get(url) as resp:
                rule = await resp.json()
                status = rule['mapping'] == 'Firefox-mozilla-central-nightly-latest'

                build_ids, appVersions = await get_release_info(rule['mapping'])

                last_build_id = max(build_ids.values())
                date = last_build_id[:8]

                old_build_id = [bid for bid in build_ids.values() if not bid.startswith(date)]

                if rule['mapping'] != 'Firefox-mozilla-central-nightly-latest':
                    status = Status.MISSING
                    message = ('Balrog rule is configured for {} ({}) instead of '
                               '"Firefox-mozilla-central-nightly-latest"')
                    message = message.format(rule['mapping'],
                                             ', '.join(sorted(set(build_ids.values()))))
                elif old_build_id:
                    platforms = [k for k, v in build_ids.items() if v in old_build_id]
                    status = Status.INCOMPLETE
                    message = ("Balrog rule is configured for {} ({}) platform {} with build ID {}"
                               " seem outdated.")
                    message = message.format(rule['mapping'],
                                             ', '.join(sorted(set(build_ids.values()))),
                                             ', '.join(platforms),
                                             ', '.join(sorted(set(old_build_id))))
                else:
                    status = Status.EXISTS
                    message = (
                        'Balrog rule is configured for the latest Nightly {} build ({}) '
                        'with an update rate of {}%')
                    message = message.format(', '.join(sorted(appVersions)),
                                             ', '.join(sorted(set(build_ids.values()))),
                                             rule['backgroundRate'])

                return build_task_response(status, url, message)

    elif channel in (Channel.BETA, Channel.AURORA):
        rule_name = 'devedition' if product == 'devedition' else 'firefox-beta'
        url = 'https://aus-api.mozilla.org/api/v1/rules/{}'.format(rule_name)
    elif channel is Channel.ESR:
        version = re.sub('esr$', '', version)
        url = 'https://aus-api.mozilla.org/api/v1/rules/esr{}'.format(version.split('.')[0])
    else:
        url = 'https://aus-api.mozilla.org/api/v1/rules/firefox-release'

    with get_session() as session:
        async with session.get(url) as resp:
            rule = await resp.json()
            build_ids, appVersions = await get_release_info(rule['mapping'])

            status = build_version_id(appVersions.pop()) >= build_version_id(version)

            exists_message = (
                'Balrog rule has been updated for {} ({}) with an update rate of {}%'
            ).format(rule['mapping'], ', '.join(sorted(set(build_ids.values()))),
                     rule['backgroundRate'])
            missing_message = 'Balrog rule is set for {} ({}) which is lower than {}'.format(
                rule['mapping'], ', '.join(sorted(set(build_ids.values()))), version)
            return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('https://aus-api.mozilla.org/__heartbeat__')
