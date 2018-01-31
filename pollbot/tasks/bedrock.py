import os.path
import re

from pyquery import PyQuery as pq

from pollbot.exceptions import TaskError
from pollbot.utils import (build_version_id, Channel, Status, get_version_channel,
                           get_version_from_filename)
from . import get_session, heartbeat_factory, build_task_response
from .archives import get_locales


async def release_notes(product, full_version):
    channel = get_version_channel(product, full_version)
    version = full_version
    if channel in (Channel.BETA, Channel.AURORA):
        parts = full_version.split('b')
        version = "{}beta".format(parts[0])
    elif channel is Channel.ESR:
        version = re.sub('esr$', '', full_version)

    if product == 'devedition':
        product = 'firefox'

    url = 'https://www.mozilla.org/en-US/{}/{}/releasenotes/'.format(product, version)

    with get_session() as session:
        async with session.get(url, allow_redirects=False) as resp:
            status = resp.status == 200

            body = await resp.text()

            localized_count = 0
            http_count = 0
            coming_soon = False

            if body:

                if 'are coming soon!' in body:
                    coming_soon = True

                d = pq(body)

                domains = ['https://addons.mozilla.org',
                           'https://www.mozilla.org',
                           'https://developer.mozilla.org',
                           'https://support.mozilla.org']

                locales = await get_locales(product, full_version)

                links = [d(n).attr('href') for n in d('#main-content a')]

                for link in links:
                    if link.startswith('http://'):
                        http_count += 1
                    else:
                        for domain in domains:
                            if link.startswith(domain):
                                for locale in locales:
                                    if '/{}/'.format(locale) in link:
                                        localized_count += 1

            exists_message = "Release notes were found for version {}".format(version)
            missing_message = "No release notes were published for version {}".format(version)
            if localized_count > 0:
                exists_message += " but {} {} should not contain the locale in the URL"
                exists_message = exists_message.format(localized_count,
                                                       'links' if localized_count > 1 else 'link')
                status = Status.INCOMPLETE

            if coming_soon:
                exists_message += ' but show a `coming soon` message.'
                status = Status.INCOMPLETE
            elif localized_count and http_count:
                exists_message += ' and '
            elif http_count:
                exists_message += ' but '
            else:
                exists_message += '.'

            if http_count > 0:
                exists_message += "{} {} should use the HTTPS protocol rather than HTTP."
                exists_message = exists_message.format(http_count,
                                                       'links' if localized_count > 1 else 'link')
                status = Status.INCOMPLETE

            return build_task_response(status, url, exists_message, missing_message)


async def security_advisories(product, version):
    channel = get_version_channel(product, version)
    url = 'https://www.mozilla.org/en-US/security/known-vulnerabilities/{}/'.format(product)
    # Security advisories are always present for BETA and NIGHTLY
    # because we don't publish any.
    if channel in (Channel.BETA, Channel.NIGHTLY):
        return build_task_response(
            status=Status.MISSING,
            link=url,
            message="Security advisories are never published for {} releases".format(
                channel.value.lower()))

    with get_session() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Security advisories page not available  ({})'.format(resp.status)
                raise TaskError(msg)
            # Does the content contains the version number?
            body = await resp.text()
            d = pq(body)

            if channel is Channel.ESR:
                version = re.sub('esr$', '', version)
                last_release = d("html").attr('data-esr-versions')
            else:
                last_release = d("html").attr('data-latest-firefox')
            status = build_version_id(last_release) >= build_version_id(version)
            message = ("Security advisories for release were "
                       "updated up to version {}".format(last_release))

            version_title = "#firefox{}".format(version.split('.')[0])
            if status and not d(version_title):
                status = Status.INCOMPLETE
                message += " but nothing was published for {} yet.".format(version_title)

            return build_task_response(status, url, message)


async def download_links(product, version):
    channel = get_version_channel(product, version)
    if channel is Channel.ESR:
        url = "https://www.mozilla.org/en-US/{}/organizations/all/".format(product)
    elif channel is Channel.RELEASE:
        url = 'https://www.mozilla.org/en-US/{}/all/'.format(product)
    else:
        url = 'https://www.mozilla.org/fr/{}/channel/desktop/'.format(product)
        if product == 'devedition':
            url = 'https://www.mozilla.org/en-US/firefox/developer/'

    with get_session() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = 'Download page not available  ({})'.format(resp.status)
                raise TaskError(msg)
            body = await resp.text()
            d = pq(body)

            if channel in (Channel.NIGHTLY, Channel.BETA, Channel.AURORA):
                if product == 'devedition':
                    link_path = "#intro-download > .download-list > .os_linux64 > a"
                elif channel is Channel.NIGHTLY:
                    link_path = "#desktop-nightly-download > .download-list > .os_linux64 > a"
                else:  # channel is Channel.BETA:
                    link_path = "#desktop-beta-download > .download-list > .os_linux64 > a"
                url = d(link_path).attr('href')
                async with session.get(url, allow_redirects=False) as resp:
                    url = resp.headers['Location']
                    filename = os.path.basename(url)
                    last_release = get_version_from_filename(filename)
            elif channel is Channel.ESR:
                version = re.sub('esr$', '', version)
                last_release = d("html").attr('data-esr-versions')
            else:
                # Does the content contains the version number?
                last_release = d("html").attr('data-latest-firefox')

            status = build_version_id(last_release) >= build_version_id(version)
            message = ("The download links for release have been published for version {}".format(
                last_release))
            return build_task_response(status, url, message)


heartbeat = heartbeat_factory('https://www.mozilla.org/en-US/firefox/all/')
