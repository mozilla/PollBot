import asyncio
import json
import os.path
from contextlib import suppress

import ruamel.yaml as yaml
from aiohttp import web

from pollbot.tasks import (
    archives, balrog, bedrock, buildhub, product_details, telemetry, bouncer
)


HERE = os.path.dirname(__file__)
VERSION_FILE = os.getenv("VERSION_FILE", "version.json")


async def version(request):
    # Use the version.json file in the current dir.
    with suppress(IOError):
        with open(VERSION_FILE) as fd:
            return web.json_response(json.load(fd))
    return web.HTTPNotFound()


def render_yaml_file(filename):
    with open(os.path.join(HERE, "..", filename)) as stream:
        content = yaml.YAML(typ='safe', pure=True).load(stream)
    return web.json_response(content)


async def oas_spec(request):
    with open(os.path.join(HERE, "..", 'api.yaml')) as stream:
        content = yaml.YAML(typ='safe', pure=True).load(stream)
    content['host'] = request.headers['Host']
    return web.json_response(content)


async def contribute_json(request):
    return render_yaml_file("contribute.yaml")


async def contribute_redirect(request):
    return web.HTTPFound('/v1/contribute.json')


async def lbheartbeat(request):
    return web.json_response({"status": "running"})


async def heartbeat(request):
    info = await asyncio.gather(archives.heartbeat(),
                                balrog.heartbeat(),
                                bedrock.heartbeat(),
                                bouncer.heartbeat(),
                                buildhub.heartbeat(),
                                product_details.heartbeat(),
                                telemetry.heartbeat(),
                                bedrock.heartbeat_tbnet())
    status = all(info) and 200 or 503
    return web.json_response({"archive": info[0],
                              "balrog": info[1],
                              "bedrock": info[2],
                              "bouncer": info[3],
                              "buildhub": info[4],
                              "product-details": info[5],
                              "telemetry": info[6],
                              "thunderbird_net": info[7]},
                             status=status)
