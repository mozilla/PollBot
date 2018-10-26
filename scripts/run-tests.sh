#!/bin/bash
# Run tests in the docker image

set -e
set -x

python3 -m venv /tmp/tests
/tmp/tests/bin/pip install -U pip
ls -l /app
ls -l /app/setup.py
/tmp/tests/bin/pip install "/app[dev]"
/tmp/tests/bin/flake8 pollbot tests
/tmp/tests/bin/py.test /app/tests
