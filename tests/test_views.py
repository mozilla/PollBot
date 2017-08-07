import json
import mock
import pytest
import os.path
import ruamel.yaml as yaml

from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app
from pollbot.exceptions import TaskError
from pollbot.views.release import status_response

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


async def check_yaml_resource(cli, url, filename):
    with open(os.path.join(HERE, "..", "pollbot", filename)) as stream:
        content = yaml.safe_load(stream)
    resp = await cli.get(url)
    assert await resp.json() == content


async def test_oas_spec(cli):
    await check_yaml_resource(cli, "/v1/__api__", "api.yaml")


async def test_contribute_json(cli):
    await check_yaml_resource(cli, "/contribute.json", "contribute.yaml")


async def test_home_body(cli):
    await check_response(cli, "/v1/", body={
        "project_name": "pollbot",
        "project_version": pollbot_version,
        "url": "https://github.com/mozilla/PollBot",
        "http_api_version": HTTP_API_VERSION
    })


async def test_status_response_handle_task_errors(cli):
    async def error_task(product, version):
        raise TaskError('Error message')
    error_endpoint = status_response(error_task)
    request = mock.MagicMock()
    request.match_info = {"product": "firefox", "version": "57.0"}
    resp = await error_endpoint(request)
    assert json.loads(resp.body.decode()) == {
        "status": "error",
        "message": "Error message",
    }


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


async def test_release_bedrock_security_advisories(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/security-advisories",
                         body={
                             "status": "exists"
                         })


async def test_release_bedrock_security_advisories_404(cli):
    await check_response(cli, "/v1/invalid-product/54.0/bedrock/security-advisories",
                         status=404, body={
                             "status": 404,
                             "message": "Invalid product: invalid-product not in ['firefox']"
                         })


async def test_release_product_details(cli):
    await check_response(cli, "/v1/firefox/54.0/product-details",
                         body={
                             "status": "exists"
                         })


async def test_release_product_details_404(cli):
    await check_response(cli, "/v1/invalid-product/54.0/product-details",
                         status=404, body={
                             "status": 404,
                             "message": "Invalid product: invalid-product not in ['firefox']"
                         })
