PollBot
=======

|coc| |travis| |master-coverage|

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

License
-------

MPL v2 (see `LICENSE <https://github.com/mozilla/PollBot/blob/master/LICENSE>`_)
