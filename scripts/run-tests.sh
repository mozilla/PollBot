#!/bin/bash
# Run tests in the docker image

set -e
set -x

export TELEMETRY_USER_ID=502
python3 -m venv /tmp/tests
/tmp/tests/bin/pip --version
/tmp/tests/bin/pip install -U pip
/tmp/tests/bin/pip --version
/tmp/tests/bin/pip install /app -e ".[dev]"
/tmp/tests/bin/flake8 pollbot tests
/tmp/tests/bin/py.test /app/tests
