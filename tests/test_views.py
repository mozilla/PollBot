import os.path
import pytest
import ruamel.yaml as yaml

from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app

HERE = os.path.dirname(__file__)


@pytest.fixture
def cli(loop, test_client):
    return loop.run_until_complete(test_client(get_app(loop=loop)))


async def check_response(cli, url, *, status=200, body=None, method="get", **kwargs):
    resp = await getattr(cli, method)(url, **kwargs)
    assert resp.status == status
    if body is not None:
        assert await resp.json() == body
    return resp


async def test_home_redirects_to_v1(cli):
    resp = await check_response(cli, "/", status=302, allow_redirects=False)
    assert resp.headers['Location'] == "/v1/"


async def test_v1_redirects_to_v1_slash(cli):
    resp = await check_response(cli, "/v1", status=302, allow_redirects=False)
    assert resp.headers['Location'] == "/v1/"


async def test_oas_spec(cli):
    with open(os.path.join(HERE, "..", "pollbot", "api.yaml"), 'r') as stream:
        oas_spec = yaml.load(stream)
    await check_response(cli, "/v1/__api__", body=oas_spec)


async def test_home_body(cli):
    await check_response(cli, "/v1/", body={
        "project_name": "pollbot",
        "project_version": pollbot_version,
        "url": "https://github.com/mozilla/PollBot",
        "http_api_version": HTTP_API_VERSION
    })


# This is currently a functional test.
async def test_release_archive(cli):
    await check_response(cli, "/v1/firefox/54.0/archive", body={
        "status": "exists"
    })


async def test_release_archive_404(cli):
    await check_response(cli, "/v1/invalid-product/54.0/archive", status=404, body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    })


async def test_release_bedrock_release_notes(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/release-notes", body={
        "status": "exists"
    })


async def test_release_bedrock_release_notes_404(cli):
    await check_response(cli, "/v1/invalid-product/54.0/bedrock/release-notes", status=404, body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    })
