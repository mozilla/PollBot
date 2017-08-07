import os.path
import pytest
import ruamel.yaml as yaml

from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app

HERE = os.path.dirname(__file__)


@pytest.fixture
def cli(loop, test_client):
    return loop.run_until_complete(test_client(get_app(loop=loop)))


async def test_home_redirects_to_v1(cli):
    resp = await cli.get("/", allow_redirects=False)
    assert resp.status == 302


async def test_oas_spec(cli):
    with open(os.path.join(HERE, "..", "pollbot", "api.yaml"), 'r') as stream:
        oas_spec = yaml.load(stream)
    resp = await cli.get("/v1/__api__")
    assert await resp.json() == oas_spec


async def test_home_body(cli):
    resp = await cli.get("/v1/")
    assert resp.status == 200
    assert await resp.json() == {
        "project_name": "pollbot",
        "project_version": pollbot_version,
        "url": "https://github.com/mozilla/PollBot",
        "http_api_version": HTTP_API_VERSION
    }


# This is currently a functional test.
async def test_release_archive(cli):
    resp = await cli.get("/v1/firefox/54.0/archive")
    assert resp.status == 200
    assert await resp.json() == {
        "status": "exists"
    }


async def test_release_archive_404(cli):
    resp = await cli.get("/v1/thunderbird/54.0/archive")
    assert resp.status == 404
    assert await resp.json() == {
        "status": 404,
        "error": "Invalid product: thunderbird not in ['firefox']"
    }


async def test_release_bedrock_release_notes(cli):
    resp = await cli.get("/v1/firefox/54.0/bedrock/release-notes")
    assert resp.status == 200
    assert await resp.json() == {
        "status": "exists"
    }


async def test_release_bedrock_release_notes_404(cli):
    resp = await cli.get("/v1/thunderbird/54.0/bedrock/release-notes")
    assert resp.status == 404
    assert await resp.json() == {
        "status": 404,
        "error": "Invalid product: thunderbird not in ['firefox']"
    }
