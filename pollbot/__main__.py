import os
from aiohttp import web
from .app import get_app

PORT = int(os.getenv("PORT", 8000))


def main():
    web.run_app(get_app(), port=PORT)
