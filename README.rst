PollBot
=======

|coc| |travis| |master-coverage| |whatsdeployed|

.. |coc| image:: https://img.shields.io/badge/%E2%9D%A4-code%20of%20conduct-blue.svg
    :target: https://github.com/mozilla/PollBot/blob/master/CODE_OF_CONDUCT.md
    :alt: Code of conduct

.. |travis| image:: https://travis-ci.org/mozilla/PollBot.svg?branch=master
    :target: https://travis-ci.org/mozilla/PollBot

.. |master-coverage| image::
    https://coveralls.io/repos/mozilla/PollBot/badge.svg?branch=master
    :alt: Coverage
    :target: https://coveralls.io/r/mozilla/PollBot

.. |readthedocs| image:: https://readthedocs.org/projects/pollbot/badge/?version=latest
    :target: https://pollbot.readthedocs.io/en/latest/
    :alt: Documentation Status

.. |pypi| image:: https://img.shields.io/pypi/v/pollbot.svg
    :target: https://pypi.python.org/pypi/pollbot

.. |whatsdeployed| image:: https://img.shields.io/badge/whatsdeployed-stage,prod-green.svg
    :target: https://whatsdeployed.io/s-olI

PollBot is an hardworking little robot (microservice) that frees its
human masters from the toilsome task of polling for the state of
things during the Firefox release process.


`Version 1.0 <https://github.com/mozilla/PollBot/projects/1>`_ will
provide, at a minimum, these API resources:

#. build exists on archive.mozilla.org
#. release notes published
#. product-details.mozilla.org JSON contains the release
#. download links are on mozilla.org and they work
#. security advisories are published and links work

Development
-----------

Create a virtualenv with Python 3.6 and then install *all* the dependencies:

.. code-block:: shell

    pip install -e ".[dev]"

Now you should be able to run the `tox` suite:

.. code-block:: shell

    tox

To start the development server you need:

``TELEMETRY_API_KEY`` - See https://sql.telemetry.mozilla.org/users/me


Equipped with these you can now run:

.. code-block:: shell

    TELEMETRY_API_KEY=yourapikey pollbot

That should start a server on ``http://0.0.0.0:8000``.

Deployment
----------

* Stage - https://pollbot.stage.mozaws.net/v1/
* Prod - https://pollbot.services.mozilla.com/v1/

Stage is automatically upgraded when new releases are made. A release is
basically a tag with the same name. To make a release run:

.. code-block:: shell

    ./bin/make-release.py --help

License
-------

MPL v2 (see `LICENSE <https://github.com/mozilla/PollBot/blob/master/LICENSE>`_)


Configuration
-------------

PollBot is a currently a stateless service, which means there are no
database services to configure.

However you can configure the following parameters using environment variables:

+-----------------------+-------------------------------------------------+
| **VARIABLE**          | **Description**                                 |
+-----------------------+-------------------------------------------------+
| ``PORT``              | The service PORT, by default runs on 9876       |
+-----------------------+-------------------------------------------------+
| ``VERSION_FILE``      | The JSON version file, default PWD/version.json |
+-----------------------+-------------------------------------------------+
| ``CACHE_MAX_AGE``     | The Cache-Control max-age value, default to 30  |
|                       | seconds. Set it to 0 to set it to no-cache      |
+-----------------------+-------------------------------------------------+
| ``TELEMETRY_API_KEY`` | API KEY to use to query the Telemetry Service   |
+-----------------------+-------------------------------------------------+
