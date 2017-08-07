import pytest
from pollbot.app import get_app


@pytest.fixture
def cli(loop, test_client):
    return loop.run_until_complete(test_client(get_app(loop=loop)))


async def check_cors(cli, url):
    resp = await cli.get(url, headers={"Origin": "http://localhost"}, allow_redirects=False)
    assert 'Access-Control-Allow-Origin' in resp.headers
    assert 'Access-Control-Allow-Credentials' in resp.headers
    assert 'Access-Control-Expose-Headers' in resp.headers


async def test_route_have_cors_enabled(cli):
    app = get_app()
    for r in app.router.resources():
        info = r.get_info()
        if 'path' in info:
            url = info['path']
        elif 'formatter' in info:
            formatter = info['formatter']
            if '{product}' in formatter:
                formatter = formatter.replace('{product}', 'firefox')
            if '{version}' in formatter:
                formatter = formatter.replace('{version}', '52.0')
        else:
            # A new case to handle
            import pdb
            pdb.set_trace()

        await check_cors(cli, url)
