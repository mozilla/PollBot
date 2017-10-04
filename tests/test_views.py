import json
import mock
import pytest
import os.path
import ruamel.yaml as yaml

from aiohttp import web, ClientError

from pollbot import __version__ as pollbot_version, HTTP_API_VERSION
from pollbot.app import get_app
from pollbot.middlewares import NO_CACHE_ENDPOINTS
from pollbot.exceptions import TaskError
from pollbot.views.release import status_response
from pollbot.utils import Status

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
    app.router.add_get('/error', error)
    app.router.add_get('/error-403', error403)
    app.router.add_get('/error-404', error404)
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


async def test_redirects_trailing_slashes(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/", status=302, allow_redirects=False)
    assert resp.headers['Location'] == "/v1/firefox/54.0"


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
        "docs": "http://127.0.0.1/v1/api/doc/"
    }, headers={"Host": "127.0.0.1"})


async def test_status_response_handle_task_errors(cli):
    async def error_task(product, version):
        raise TaskError('Error message')
    error_endpoint = status_response(error_task)
    request = mock.MagicMock()
    request.match_info = {"product": "firefox", "version": "57.0"}
    resp = await error_endpoint(request)
    assert json.loads(resp.body.decode()) == {
        "status": Status.ERROR.value,
        "message": "Error message",
    }


async def test_status_response_handle_client_errors(cli):
    async def error_task(product, version):
        raise ClientError('Error message')
    error_endpoint = status_response(error_task)
    request = mock.MagicMock()
    request.match_info = {"product": "firefox", "version": "57.0"}
    resp = await error_endpoint(request)
    assert json.loads(resp.body.decode()) == {
        "status": Status.ERROR.value,
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


async def test_status_response_validates_version(cli):
    async def dummy_task(product, version):
        return True
    error_endpoint = status_response(dummy_task)
    request = mock.MagicMock()
    request.match_info = {"product": "firefox", "version": "invalid-version"}
    resp = await error_endpoint(request)
    assert resp.status == 404
    assert json.loads(resp.body.decode()) == {
        "status": 404,
        "message": "Invalid version number: invalid-version",
    }


async def test_get_releases_response_validates_product_name(cli):
    await check_response(cli, "/v1/invalid-product", body={
        "status": 404,
        "message": "Invalid product: invalid-product not in ['firefox']"
    }, status=404)


async def test_get_releases_response_validates_version(cli):
    await check_response(cli, "/v1/firefox/invalid-version", body={
        "status": 404,
        "message": "Invalid version number: invalid-version"
    }, status=404)


async def test_403_errors_are_json_responses(cli):
    await check_response(cli, "/error-403", body={
        "status": 403,
        "message": "Forbidden"
    }, status=403)


async def test_404_pages_are_json_responses(cli):
    await check_response(cli, "/not-found", body={
        "status": 404,
        "message": "Page '/not-found' not found"
    }, status=404)


async def test_handle_views_that_return_404_pages_are_json_responses(cli):
    await check_response(cli, "/error-404", body={
        "status": 404,
        "message": "Page '/error-404' not found"
    }, status=404)


async def test_500_pages_are_json_responses(cli):
    await check_response(cli, "/error", body={
        "status": 503,
        "message": "Service currently unavailable"
    }, status=503)


async def test_get_checks_for_nightly(cli):
    await check_response(cli, "/v1/firefox/57.0a1", body={
        "product": "firefox",
        "version": "57.0a1",
        "channel": "nightly",
        "checks": [
            {"url": "http://localhost/v1/firefox/57.0a1/archive", "title": "Archive Release"},
            {"url": "http://localhost/v1/firefox/57.0a1/balrog-rules",
             "title": "Balrog update rules"},
            {"url": "http://localhost/v1/firefox/57.0a1/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/57.0a1/product-details",
             "title": "Product details"},
            {"url": "http://localhost/v1/firefox/57.0a1/bedrock/release-notes",
             "title": "Release notes"},
            {"url": "http://localhost/v1/firefox/57.0a1/telemetry/update-parquet-uptake",
             "title": "Telemetry Update Parquet Uptake"},
        ]
    })


async def test_get_checks_for_beta(cli):
    await check_response(cli, "/v1/firefox/56.0b6", body={
        "product": "firefox",
        "version": "56.0b6",
        "channel": "beta",
        "checks": [
            {"url": "http://localhost/v1/firefox/56.0b6/archive", "title": "Archive Release"},
            {"url": "http://localhost/v1/firefox/56.0b6/balrog-rules",
             "title": "Balrog update rules"},
            {"url": "http://localhost/v1/firefox/56.0b6/buildhub",
             "title": "Buildhub release info"},
            {"url": "http://localhost/v1/firefox/56.0b6/crash-stats/uptake",
             "title": "Crash Stats Uptake"},
            {"url": "http://localhost/v1/firefox/56.0b6/product-details"
             "/devedition-beta-versions-matches",
             "title": "Devedition and Beta versions matches"},
            {"url": "http://localhost/v1/firefox/56.0b6/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/56.0b6/archive/partner-repacks",
             "title": "Partner repacks"},
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
            {"url": "http://localhost/v1/firefox/54.0/balrog-rules",
             "title": "Balrog update rules"},
            {"url": "http://localhost/v1/firefox/54.0/buildhub",
             "title": "Buildhub release info"},
            {"url": "http://localhost/v1/firefox/54.0/crash-stats/uptake",
             "title": "Crash Stats Uptake"},
            {"url": "http://localhost/v1/firefox/54.0/bedrock/download-links",
             "title": "Download links"},
            {"url": "http://localhost/v1/firefox/54.0/archive/partner-repacks",
             "title": "Partner repacks"},
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
            {"url": "http://localhost/v1/firefox/52.3.0esr/balrog-rules",
             "title": "Balrog update rules"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/buildhub",
             "title": "Buildhub release info"},
            {"url": "http://localhost/v1/firefox/52.3.0esr/crash-stats/uptake",
             "title": "Crash Stats Uptake"},
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


# These are currently functional tests.

async def test_nightly_archive(cli):
    resp = await check_response(cli, "/v1/firefox/57.0a1/archive")
    body = await resp.json()
    assert body['status'] in (Status.EXISTS.value, Status.INCOMPLETE.value)
    assert 'firefox/nightly/latest-mozilla-central-l10n' in body['message']
    assert body['link'] == ("https://archive.mozilla.org/pub/firefox/nightly/"
                            "latest-mozilla-central-l10n/")


async def test_release_archive(cli):
    await check_response(cli, "/v1/firefox/54.0/archive", body={
        "status": Status.EXISTS.value,
        "message": "The archive exists at https://archive.mozilla.org/pub/firefox/releases/54.0/ "
        "and all 94 locales are present for all platforms "
        "(linux-i686, linux-x86_64, mac, win32, win64)",
        "link": "https://archive.mozilla.org/pub/firefox/releases/54.0/"
    })


async def test_beta_archive(cli):
    await check_response(cli, "/v1/firefox/56.0b10/archive", body={
        "status": Status.EXISTS.value,
        "message": "The archive exists at https://archive.mozilla.org/pub/firefox/releases/56.0b10"
        "/ and all 95 locales are present for all platforms "
        "(linux-i686, linux-x86_64, mac, win32, win64)",
        "link": "https://archive.mozilla.org/pub/firefox/releases/56.0b10/"
    })


async def test_esr_archive(cli):
    await check_response(cli, "/v1/firefox/52.3.0esr/archive", body={
        "status": Status.EXISTS.value,
        "message": "The archive exists at https://archive.mozilla.org/pub/firefox/releases/"
        "52.3.0esr/ and all 92 locales are present for all platforms "
        "(linux-i686, linux-x86_64, mac, win32, win64)",
        "link": "https://archive.mozilla.org/pub/firefox/releases/52.3.0esr/"
    })


async def test_release_partner_repacks(cli):
    await check_response(cli, "/v1/firefox/54.0/archive/partner-repacks", body={
        "status": Status.EXISTS.value,
        "message": "partner-repacks found in https://archive.mozilla.org/pub/"
        "firefox/candidates/54.0-candidates/build3/",
        "link": "https://archive.mozilla.org/pub/firefox/candidates/54.0-candidates/build3/"
    })


async def test_beta_partner_repacks(cli):
    await check_response(cli, "/v1/firefox/56.0b10/archive/partner-repacks", body={
        "status": Status.EXISTS.value,
        "message": "partner-repacks found in https://archive.mozilla.org/pub/"
        "firefox/candidates/56.0b10-candidates/build1/",
        "link": "https://archive.mozilla.org/pub/firefox/candidates/56.0b10-candidates/build1/"
    })


async def test_esr_crash_stats_uptake(cli):
    resp = await check_response(cli, "/v1/firefox/52.2.1esr/crash-stats/uptake")
    body = await resp.json()
    assert body['status'] == Status.INCOMPLETE.value
    assert body['link'].startswith("https://crash-stats.mozilla.com/api/ADI/")
    assert body['message'].startswith("Crash-Stats uptake for version 52.2.1esr is")


async def test_release_crash_stats_uptake(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/crash-stats/uptake")
    body = await resp.json()
    assert body['status'] == Status.INCOMPLETE.value
    assert body['link'].startswith("https://crash-stats.mozilla.com/api/ADI/")
    assert body['message'].startswith("Crash-Stats uptake for version 54.0 is")


async def test_beta_crash_stats_uptake(cli):
    resp = await check_response(cli, "/v1/firefox/56.0b10/crash-stats/uptake")
    body = await resp.json()
    assert body['status'] == Status.INCOMPLETE.value
    assert body['link'].startswith("https://crash-stats.mozilla.com/api/ADI/")
    assert body['message'].startswith("Crash-Stats uptake for version 56.0b10 is")


async def test_release_balrog_rules(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/balrog-rules")
    body = await resp.json()
    assert body["status"] in (Status.EXISTS.value, Status.INCOMPLETE.value)
    assert "Balrog rule has been updated" in body["message"]
    assert body["link"] == "https://aus-api.mozilla.org/api/v1/rules/firefox-release"


async def test_release_buildhub_rules(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/buildhub")
    body = await resp.json()
    assert body["status"] == Status.EXISTS.value
    assert "Buildhub contains information about this release." in body["message"]
    assert body["link"] == ("https://mozilla-services.github.io/buildhub/"
                            "?versions[0]=54.0&products[0]=firefox")


async def test_release_bedrock_release_notes(cli):
    await check_response(cli, "/v1/firefox/54.0/bedrock/release-notes", body={
        "status": Status.EXISTS.value,
        "message": "Release notes were found for version 54.0",
        "link": "https://www.mozilla.org/en-US/firefox/54.0/releasenotes/"
    })


async def test_release_bedrock_security_advisories(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/bedrock/security-advisories")
    body = await resp.json()
    assert body['status'] == Status.EXISTS.value
    assert body['message'].startswith("Security advisories for release were published")
    assert body['link'] == "https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox/"


async def test_release_bedrock_download_links(cli):
    resp = await check_response(cli, "/v1/firefox/54.0/bedrock/download-links")
    body = await resp.json()

    assert body['status'] == Status.EXISTS.value
    assert body['message'].startswith("The download links for release have been published")
    assert body['link'] == "https://www.mozilla.org/en-US/firefox/all/"


async def test_release_product_details(cli):
    await check_response(cli, "/v1/firefox/54.0/product-details", body={
        "status": Status.EXISTS.value,
        "message": "We found product-details information about version 54.0",
        "link": "https://product-details.mozilla.org/1.0/firefox.json"
    })


async def test_beta_product_details_devedition_and_beta_versions_matches(cli):
    await check_response(cli,
                         "/v1/firefox/56.0b7/product-details/devedition-beta-versions-matches",
                         status=200)


async def test_release_product_details_devedition_and_beta_versions_matches(cli):
    url = "/v1/firefox/54.0/product-details/devedition-beta-versions-matches"
    await check_response(cli, url, body={
        "status": Status.MISSING.value,
        "message": "No devedition and beta check for 'release' releases",
        "link": "https://product-details.mozilla.org/1.0/firefox_versions.json"
    })


async def test_esr_balrog_rules(cli):
    resp = await check_response(cli, "/v1/firefox/52.3.0esr/balrog-rules")
    body = await resp.json()
    assert body["status"] == Status.EXISTS.value
    assert "Balrog rule has been updated" in body["message"]
    assert body["link"] == "https://aus-api.mozilla.org/api/v1/rules/esr52"


async def test_beta_balrog_rules(cli):
    resp = await check_response(cli, "/v1/firefox/56.0b7/balrog-rules")
    body = await resp.json()
    assert body["status"] == Status.EXISTS.value
    assert "Balrog rule has been updated" in body["message"]
    assert body["link"] == "https://aus-api.mozilla.org/api/v1/rules/firefox-beta"


async def test_nightly_balrog_rules(cli):
    resp = await check_response(cli, "/v1/firefox/57.0a1/balrog-rules")
    body = await resp.json()
    assert "Balrog rule is configured" in body["message"]
    assert body["status"] in (Status.EXISTS.value, Status.MISSING.value, Status.INCOMPLETE.value)
    assert body["link"] == "https://aus-api.mozilla.org/api/v1/rules/firefox-nightly"


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
                         status=503,
                         body={
                             "archive": True,
                             "balrog": True,
                             "bedrock": True,
                             "buildhub": True,
                             "crash-stats": True,
                             "product-details": True,
                             "telemetry": False,
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


@pytest.mark.parametrize("endpoint", NO_CACHE_ENDPOINTS)
async def test_endpoint_have_got_cache_control_headers(cli, endpoint):
    resp = await cli.get(endpoint)
    assert "Cache-Control" in resp.headers
    assert resp.headers["Cache-Control"] == "no-cache"


async def test_product_endpoint_have_got_cache_control_headers(cli):
    resp = await cli.get("/v1/firefox/54.0")
    assert "Cache-Control" in resp.headers
    assert resp.headers["Cache-Control"] == "public; max-age=30"


async def test_cache_control_header_max_age_can_be_parametrized(cli):
    with mock.patch("pollbot.middlewares.CACHE_MAX_AGE", 10):
        resp = await cli.get("/v1/firefox/54.0")
        assert "Cache-Control" in resp.headers
        assert resp.headers["Cache-Control"] == "public; max-age=10"
