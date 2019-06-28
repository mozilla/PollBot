PollBot
=======

.. image:: https://img.shields.io/badge/%E2%9D%A4-code%20of%20conduct-blue.svg
   :alt: Code of conduct
   :target: https://github.com/mozilla/PollBot/blob/master/CODE_OF_CONDUCT.md
.. image:: https://travis-ci.org/mozilla/PollBot.svg?branch=master
   :alt: Travis CI status
   :target: https://travis-ci.org/mozilla/PollBot
.. image:: https://coveralls.io/repos/mozilla/PollBot/badge.svg?branch=master
   :alt: Coverage
   :target: https://coveralls.io/r/mozilla/PollBot
.. image:: https://readthedocs.org/projects/pollbot/badge/?version=latest
   :alt: Documentation Status
   :target: https://pollbot.readthedocs.io/en/latest/
.. image:: https://img.shields.io/pypi/v/pollbot.svg
   :alg: PyPI
   :target: https://pypi.python.org/pypi/pollbot
.. image:: https://img.shields.io/badge/whatsdeployed-stage,prod-green.svg
   :alt: What's Deployed
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

Create a local dev environment:

.. code-block:: shell

   make build

Then you can run various dev-related tasks. For a list, see:

.. code-block:: shell

   make help

To start the development server you need this in your ``.env``:

``TELEMETRY_API_KEY`` - See https://sql.telemetry.mozilla.org/users/me

Equipped with these you can now run PollBot:

.. code-block:: shell

   make run

That should start a server on ``http://localhost:9876``.

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
