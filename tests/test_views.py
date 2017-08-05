import pytest
from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app


@pytest.fixture
def cli(loop, test_client):
    return loop.run_until_complete(test_client(get_app(loop=loop)))


async def test_home_redirects_to_v1(cli):
    resp = await cli.get("/", allow_redirects=False)
    assert resp.status == 302


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
async def test_release_body(cli):
    resp = await cli.get("/v1/firefox/54.0")
    assert resp.status == 200
    assert await resp.json() == {
        "product": "firefox",
        "version": "54.0",
        "releasenotes": True
    }
