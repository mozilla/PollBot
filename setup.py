import codecs
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read_file(filename):
    """Open a related file and return its content."""
    with codecs.open(os.path.join(here, filename), encoding='utf-8') as f:
        content = f.read()
    return content


README = read_file('README.rst')
CHANGELOG = read_file('CHANGELOG.rst')
CONTRIBUTORS = read_file('CONTRIBUTORS.rst')

REQUIREMENTS = [
    'aiohttp<3',
    'aiohttp_cors',
    'aiohttp-swagger',
    'ruamel.yaml',
    'pyquery',
]

ENTRY_POINTS = {
    'console_scripts': [
        'pollbot = pollbot.__main__:main'
    ]
}

DEV_REQUIREMENTS = {
    "docs": [],
    "tests": [
        "aioresponses",
        "asynctest",
        "flake8",
        "mock",
        "pytest",
        "pytest-aiohttp",
        "pytest-cache",
        "pytest-cover",
        "pytest-sugar",
        "swagger-spec-validator",
        "tox",
        "wheel",
        "zest.releaser",
        "aiohttp<3",
    ]
}

setup(
    name='pollbot',
    version='1.3.0.dev0',
    description='A service that polls other services about releases deliveries.',
    long_description="{}\n\n{}\n\n{}".format(README, CHANGELOG, CONTRIBUTORS),
    license='Mozilla Public License 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)"
    ],
    keywords="web sync json storage services",
    author='Mozilla Services',
    author_email='storage-team@mozilla.com',
    url='https://github.com/mozilla/PollBot',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    extras_require={
        "docs": DEV_REQUIREMENTS["docs"],
        "tests": DEV_REQUIREMENTS["tests"],
        "dev": DEV_REQUIREMENTS["docs"] + DEV_REQUIREMENTS["tests"],
    },
    test_suite="tests",
    entry_points=ENTRY_POINTS,
)
