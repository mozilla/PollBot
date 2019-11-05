import os.path


from pollbot.exceptions import TaskError
from pollbot.utils import (build_version_id, Channel, get_version_channel,
                           get_version_from_filename)
from . import get_session, heartbeat_factory, build_task_response


async def bouncer(product, version):
    """Make sure bouncer redirects to the expected version (or a later one)."""
    channel = get_version_channel(product, version)
    channel_value = channel.value

    if product == 'devedition':
        channel_value = "DEVEDITION"
    if channel == Channel.RELEASE:
        product_channel = 'firefox'
    else:
        product_channel = 'firefox-{}'.format(channel_value.lower())
    url = 'https://download.mozilla.org?product={}-latest-ssl&os=linux64&lang=en-US'.format(
            product_channel)

    async with get_session() as session:
        async with session.get(url, allow_redirects=False) as resp:
            if resp.status == 302:
                url = resp.headers['Location']
            else:
                msg = 'Bouncer is down ({}).'.format(resp.status)
                raise TaskError(msg, url=url)

            filename = os.path.basename(url)
            last_release = get_version_from_filename(filename)
            status = build_version_id(last_release) >= build_version_id(version)
            message = "Bouncer for {} redirects to version {}".format(channel_value, last_release)
            return build_task_response(status, url, message)


heartbeat = heartbeat_factory('https://download.mozilla.org/')
