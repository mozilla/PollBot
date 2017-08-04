from aiohttp import web
from .app import get_app


def main():
    web.run_app(get_app(), port=8000)
