import asyncio
from collections import defaultdict
from pollbot.exceptions import TaskError
from pollbot.utils import Status, Channel, get_version_channel
from . import get_session, heartbeat_factory, build_task_response


NIGHTLY_PLATFORMS = {
    "windows": "Firefox Installer.{locale}.exe",
    "win32": "firefox-{version}.{locale}.win32.installer.exe",
    "win64": "firefox-{version}.{locale}.win64.installer.exe",
    "linux32": "firefox-{version}.{locale}.linux-i686.tar.bz2",
    "linux64": "firefox-{version}.{locale}.linux-x86_64.tar.bz2",
    "mac": "firefox-{version}.{locale}.mac.dmg",
}


RELEASE_PLATFORMS = [
    'linux-i686',
    'linux-x86_64',
    'mac',
    'win32',
    'win64',
]


async def get_locales(product, version):
    channel = get_version_channel(version)
    tag = "{}_{}_RELEASE".format(product.upper(), version.replace('.', '_'))
    if channel is Channel.NIGHTLY:
        url = "https://hg.mozilla.org/mozilla-central/raw-file/tip/browser/locales/all-locales"
    elif channel is Channel.BETA:
        url = ("https://hg.mozilla.org/releases/mozilla-beta/raw-file/{}/"
               "browser/locales/shipped-locales").format(tag)
    elif channel is Channel.RELEASE:
        url = ("https://hg.mozilla.org/releases/mozilla-release/raw-file/{}/"
               "browser/locales/shipped-locales").format(tag)
    else:
        major, _ = version.split('.', 1)
        branch = "mozilla-esr{}".format(major)
        url = ("https://hg.mozilla.org/releases/{}/raw-file/{}/"
               "browser/locales/shipped-locales").format(branch, tag)

    with get_session() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                msg = '{} not available (HTTP {})'.format(url, resp.status)
                raise TaskError(msg)
            hg_locales = []
            body = await resp.text()
            for line in body.split('\n'):
                try:
                    locale, _ = line.split(' ', 1)
                except ValueError:
                    locale = line
                # We ignore here ja-JP-mac since because it is ja for the mac platform.
                # And we want them to be considered as the same locale.
                if locale and locale != 'ja-JP-mac':
                    hg_locales.append(locale)

            return hg_locales


def verdict(url, locales, missing_locales, missing_files):
    status = Status.EXISTS
    message = (
        "The archive exists at {} and all {} locales are present "
        "for all platforms ({})").format(
            url, len(locales), ', '.join(RELEASE_PLATFORMS))

    if missing_files or missing_locales:
        status = Status.INCOMPLETE
        missing = ""
        verb = "is"
        if missing_locales:
            missing = "{} locale{}".format(", ".join(sorted(missing_locales)),
                                           's' if len(missing_locales) > 1 else '')
            if missing_files:
                missing += " and "
        if missing_files:
            missing += "{} locale file{}".format(", ".join(sorted(missing_files)),
                                                 's' if len(missing_files) > 1 else '')
        if len(missing_files) + len(missing_locales) > 1:
            verb = "are"

        message = "{missing} {verb} missing at {url}".format(
            missing=missing,
            verb=verb,
            url=url)

    return status, message


async def check_nightly_releases_files(url, files, product, version):
    locales = await get_locales(product, version)
    missing_locales = []
    missing_files = []
    # Make sure all locales are present
    for locale in locales:
        missing_files_for_locale = []
        for platform, platform_pattern in NIGHTLY_PLATFORMS.items():
            current_locale = locale
            if platform == 'mac' and locale == 'ja':
                # https://github.com/mozilla/bedrock/ \
                # blob/d55993a32d6571ce0df1aae62379d94a096324c7/ \
                # bedrock/firefox/firefox_details.py#L221
                current_locale = 'ja-JP-mac'
            filename = platform_pattern.format_map(dict(version=version,
                                                        locale=current_locale))
            if filename not in files:
                missing_files_for_locale.append(filename)
        if len(missing_files_for_locale) == len(NIGHTLY_PLATFORMS):
            # All platform files where missing for this locale.
            # The locale is missing from the release.
            missing_locales.append(locale)
        elif missing_files_for_locale:
            # Only some files where missing.
            # Add them the list of mising files.
            missing_files.extend(missing_files_for_locale)

    return verdict(url, locales, missing_locales, missing_files)


async def get_platform_locale(url, platform):
    with get_session() as session:
        url = '{}/{}/'.format(url.rstrip('/'), platform)
        async with session.get(url, headers={"Accept": "application/json"}) as resp:
            if resp.status != 200:
                msg = 'Archive CDN not available; failing to get {} (HTTP {})'.format(
                    url, resp.status)
                raise TaskError(msg)

            body = await resp.json()
            return sorted([p.strip('/') for p in body['prefixes'] if not p.startswith('xpi')])


async def check_releases_files(url, product, version):
    # Make sure all platforms have got the same locale set.
    responses = await asyncio.gather(
        get_locales(product, version),
        *[get_platform_locale(url, platform) for platform in RELEASE_PLATFORMS]
    )

    locales = set(responses[0])
    platform_locales = map(set, responses[1:])

    missing = defaultdict(set)

    # Make sure the platform locale set matches the expected one.
    for i, platform_locale in enumerate(platform_locales):
        platform = RELEASE_PLATFORMS[i]
        if platform == 'mac' and 'ja-JP-mac' in platform_locale:
                platform_locale.add('ja')
                platform_locale.remove('ja-JP-mac')
        for d in locales ^ platform_locale:
            missing[d].add(platform)

    missing_locales = []
    missing_files = []
    for locale, platforms in missing.items():
        if len(platforms) < len(RELEASE_PLATFORMS):
            for platform in platforms:
                if platform.startswith('mac') and locale == 'ja':
                    locale = 'ja-JP-mac'
                missing_files.append("{} for {}".format(locale, platform))
        else:
            missing_locales.append(locale)

    return verdict(url, locales, missing_locales, missing_files)


async def archives(product, version):
    with get_session() as session:
        channel = get_version_channel(version)
        if channel is Channel.NIGHTLY:
            url = 'https://archive.mozilla.org/pub/{}/nightly/latest-mozilla-central-l10n/'.format(
                product)
            message = "No archive found at {}".format(url)

            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    success = False
                else:
                    body = await resp.json()
                    files = sorted([r["name"] for r in body["files"]
                                    if r["name"].lower().startswith(product) and
                                    not r["name"].endswith('mar')],
                                   reverse=True)

                    success, message = await check_nightly_releases_files(
                        url, files, product, version)

                return build_task_response(success, url, message)
        else:
            url = 'https://archive.mozilla.org/pub/{}/releases/{}/'.format(product, version)
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status >= 500:
                    msg = 'Archive CDN not available (HTTP {})'.format(resp.status)
                    raise TaskError(msg)
                success = resp.status < 400
                message = ("No archive found for this version number at "
                           "https://archive.mozilla.org/pub/{}/releases/".format(product))
                if success:
                    success, message = await check_releases_files(url, product, version)
                return build_task_response(success, url, message)


heartbeat = heartbeat_factory('https://archive.mozilla.org/pub/firefox/releases/')
