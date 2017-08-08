import asyncio
import json
import os.path
from contextlib import suppress

import ruamel.yaml as yaml
from aiohttp import web

from pollbot.tasks import archives, bedrock, product_details


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
        content = yaml.safe_load(stream)
    return web.json_response(content)


async def oas_spec(request):
    return render_yaml_file("api.yaml")


async def contribute_json(request):
    return render_yaml_file("contribute.yaml")


async def lbheartbeat(request):
    return web.json_response({"status": "running"})


async def heartbeat(request):
    info = await asyncio.gather(archives.heartbeat(),
                                bedrock.heartbeat(),
                                product_details.heartbeat())
    status = all(info) and 200 or 503
    return web.json_response({"archive": info[0],
                              "bedrock": info[1],
                              "product-details": info[2]},
                             status=status)
