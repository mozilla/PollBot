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

# Note: Requirements are maintained in the requirements.txt file.

setup(
    name='pollbot',
    version='1.5.0',
    description='A service that polls other services about releases deliveries.',
    long_description="{}\n\n{}\n\n{}".format(README, CHANGELOG, CONTRIBUTORS),
    license='Mozilla Public License 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
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
    entry_points={
        'console_scripts': ['pollbot=pollbot.__main__:main']
    },
)
