import os.path

from aiohttp import web
import ruamel.yaml as yaml

HERE = os.path.dirname(__file__)


async def oas_spec(request):
    with open(os.path.join(HERE, "..", "api.yaml")) as stream:
        oas_spec = yaml.safe_load(stream)
    return web.json_response(oas_spec)


async def contribute_json(request):
    with open(os.path.join(HERE, "..", "contribute.yaml")) as stream:
        contribute = yaml.safe_load(stream)
    return web.json_response(contribute)
