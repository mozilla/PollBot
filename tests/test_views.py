import json
import mock
import pytest
import os.path
import ruamel.yaml as yaml

from aiohttp import web

from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app
from pollbot.exceptions import TaskError
from pollbot.views.release import status_response

HERE = os.path.dirname(__file__)


@pytest.fixture
def cli(loop, test_client):
    async def error403(request):
        raise web.HTTPForbidden()

    async def error404(request):
        return web.HTTPNotFound()

    async def error(request):
        raise ValueError()

    app = get_app(loop=loop)
    app.router.add_get('/v1/error/', error)
    app.router.add_get('/v1/error-403/', error403)
    app.router.add_get('/v1/error-404/', error404)
    return loop.run_until_complete(test_client(app))


async def check_response(cli, url, *, status=200, body=None, method="get", **kwargs):
    resp = await getattr(cli, method)(url, **kwargs)
    assert resp.status == status
    text = json.dumps(body)
    text = text.replace('http://localhost/', '{}://{}:{}/'.format(
        resp.url.scheme, resp.url.host, resp.url.port))
    if body is not None:
        assert await resp.json() == json.loads(text)
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


async def test_contribute_redirect(cli):
    resp = await check_response(cli, "/contribute.json", status=302, allow_redirects=False)
    assert resp.headers['Location'] == "/v1/contribute.json"


async def test_contribute_json(cli):
    await check_yaml_resource(cli, "/v1/contribute.json", "contribute.yaml")


async def test_home_body(cli):
    await check_response(cli, "/v1/", body={
        "project_name": "pollbot",
        "project_version": pollbot_version,
        "url": "https://github.com/mozilla/PollBot",
        "http_api_version": HTTP_API_VERSION,
        "docs": "http://127.0.0.1/v1/api/doc"
    }, headers={"Host": "127.0.0.1"})


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


async def test_status_response_validates_product_name(cli):
    async def dummy_task(product, version):
        return True
    error_endpoint = status_response(dummy_task)
    request = mock.MagicMock()
    request.match_info = {"product": "invalid-product", "version": "57.0"}
    resp = await error_endpoint(request)
    assert resp.status == 404
    assert json.loads(resp.body.decode()) == {
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']",
    }


async def test_get_releases_response_validates_product_name(cli):
    await check_response(cli, "/v1/invalid-product", body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    }, status=404)


async def test_403_errors_are_json_responses(cli):
    await check_response(cli, "/v1/error-403/", body={
        "status": 403,
        "message": "Forbidden"
    }, status=403)


async def test_404_pages_are_json_responses(cli):
    await check_response(cli, "/v1/not-found/", body={
        "status": 404,
        "message": "Page '/v1/not-found/' not found"
    }, status=404)


async def test_handle_views_that_return_404_pages_are_json_responses(cli):
    await check_response(cli, "/v1/error-404/", body={
        "status": 404,
        "message": "Page '/v1/error-404/' not found"
    }, status=404)


async def test_500_pages_are_json_responses(cli):
    await check_response(cli, "/v1/error/", body={
        "status": 503,
        "message": "Service currently unavailable"
    }, status=503)


async def test_get_checks_for_nightly(cli):
    await check_response(cli, "/v1/firefox/57.0a1", body={
        "product": "firefox",
        "version": "57.0a1",
        "channel": "nightly",
        "checks": [
            {"url": "http://localhost/v1/firefox/57.0a1/archive-date", "title": "Archive Date"},
            {"url": "http://localhost/v1/firefox/57.0a1/archive-date-l10n",
             "title": "Archive Date l10n"},
            {"url": "http://localhost/v1/firefox/57.0a1/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/57.0a1/product-details",
             "title": "Product details"},
            {"url": "http://localhost/v1/firefox/57.0a1/bedrock/release-notes",
             "title": "Release notes"}
        ]
    })


async def test_get_checks_for_beta(cli):
    await check_response(cli, "/v1/firefox/56.0b6", body={
        "product": "firefox",
        "version": "56.0b6",
        "channel": "beta",
        "checks": [
            {"url": "http://localhost/v1/firefox/56.0b6/archive", "title": "Archive Release"},
            {"url": "http://localhost/v1/firefox/56.0b6/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/56.0b6/product-details",
             "title": "Product details"},
            {"url": "http://localhost/v1/firefox/56.0b6/bedrock/release-notes",
             "title": "Release notes"},
        ]
    })


async def test_get_checks_for_release(cli):
    await check_response(cli, "/v1/firefox/54.0", body={
        "product": "firefox",
        "version": "54.0",
        "channel": "release",
        "checks": [
            {"url": "http://localhost/v1/firefox/54.0/archive", "title": "Archive Release"},
            {"url": "http://localhost/v1/firefox/54.0/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/54.0/product-details",
             "title": "Product details"},
            {"url": "http://localhost/v1/firefox/54.0/bedrock/release-notes",
             "title": "Release notes"},
            {"url": "http://localhost/v1/firefox/54.0/bedrock/security-advisories",
             "title": "Security advisories"},
        ]
    })


async def test_get_checks_for_esr(cli):
    await check_response(cli, "/v1/firefox/52.3.0esr", body={
        "product": "firefox",
        "version": "52.3.0esr",
        "channel": "esr",
        "checks": [
            {"url": "http://localhost/v1/firefox/52.3.0esr/archive", "title": "Archive Release"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/product-details",
             "title": "Product details"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/bedrock/release-notes",
             "title": "Release notes"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/bedrock/security-advisories",
             "title": "Security advisories"},
        ]
    })


async def test_get_checks_response_validates_product_name(cli):
    await check_response(cli, "/v1/invalid-product/56.0", body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    }, status=404)


# This is currently a functional test.
async def test_release_archive_date(cli):
    await check_response(cli, "/v1/firefox/57.0a1/archive-date", body={
        "status": "exists"
    })


async def test_release_archive_date_with_wrong_version_number(cli):
    await check_response(cli, "/v1/firefox/56.0b1/archive-date", body={
        "status": "missing"
    })


async def test_release_archive_date_l10n(cli):
    await check_response(cli, "/v1/firefox/57.0a1/archive-date-l10n", body={
        "status": "exists"
    })


async def test_release_archive_date_l10n_with_wrong_version_number(cli):
    await check_response(cli, "/v1/firefox/56.0b1/archive-date-l10n", body={
        "status": "missing"
    })


async def test_release_archive(cli):
    await check_response(cli, "/v1/firefox/54.0/archive", body={
        "status": "exists"
    })


async def test_release_bedrock_release_notes(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/release-notes", body={
        "status": "exists"
    })


async def test_release_bedrock_security_advisories(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/security-advisories",
                         body={
                             "status": "exists"
                         })


async def test_release_bedrock_download_links(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/download-links",
                         body={
                             "status": "exists"
                         })


async def test_release_product_details(cli):
    await check_response(cli, "/v1/firefox/54.0/product-details",
                         body={
                             "status": "exists"
                         })


async def test_releases_list(cli):
    resp = await check_response(cli, "/v1/firefox")
    body = await resp.json()
    assert "releases" in body
    assert all([isinstance(version, str) for version in body["releases"]])


# Utilities
async def test_lbheartbeat(cli):
    await check_response(cli, "/v1/__lbheartbeat__",
                         body={
                             "status": "running"
                         })


async def test_heartbeat(cli):
    await check_response(cli, "/v1/__heartbeat__",
                         body={
                             "archive": True,
                             "bedrock": True,
                             "product-details": True,
                         })


async def test_version_view_return_404_if_missing_file(cli):
    with mock.patch("builtins.open", side_effect=IOError):
        await check_response(cli, "/v1/__version__",
                             status=404,
                             body={
                                 "status": 404,
                                 "message": "Page '/v1/__version__' not found"
                             })


async def test_version_view_return_200(cli):
    with open("version.json") as fd:
        await check_response(cli, "/v1/__version__",
                             body=json.load(fd))


async def test_ongoing_versions_response_validates_product_name(cli):
    await check_response(cli, "/v1/invalid-product/ongoing-versions", body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    }, status=404)


async def test_ongoing_versions_view(cli):
    resp = await check_response(cli, "/v1/firefox/ongoing-versions")
    body = await resp.json()
    assert "esr" in body
    assert "release" in body
    assert "beta" in body
    assert "nightly" in body
