from . import get_session, build_task_response, heartbeat_factory

BUILDHUB_SERVER = "https://buildhub.stage.mozaws.net/v1"


async def buildhub(product, version):
    url = '{}/buckets/build-hub/collections/releases/records?source.product={}&target.version="{}"'
    url = url.format(BUILDHUB_SERVER, product, version)

    with get_session() as session:
        async with session.get(url) as resp:
            body = await resp.json()
            status = len(body['data']) > 0
            exists_message = 'Buildhub contains information about this release.'
            missing_message = 'Buildhub does not contain any information about this release yet.'
            url = "https://mozilla-services.github.io/buildhub/?versions[0]={}&products[0]={}"
            url = url.format(version, product)
            return build_task_response(status, url, exists_message, missing_message)


heartbeat = heartbeat_factory('{}/__heartbeat__'.format(BUILDHUB_SERVER))
