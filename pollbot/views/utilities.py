import os.path

from aiohttp import web
import ruamel.yaml as yaml

HERE = os.path.dirname(__file__)


def render_yaml_file(filename):
    with open(os.path.join(HERE, "..", filename)) as stream:
        content = yaml.safe_load(stream)
    return web.json_response(content)


async def oas_spec(request):
    return render_yaml_file("api.yaml")


async def contribute_json(request):
    return render_yaml_file("contribute.yaml")
