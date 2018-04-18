#!/bin/bash
# Run tests in the docker image
export TELEMETRY_USER_ID=502
python3 -m venv /tmp/tests
/tmp/tests/bin/pip install -r /app/dev-requirements.txt
/tmp/tests/bin/pip install /app
/tmp/tests/bin/flake8 pollbot tests
/tmp/tests/bin/py.test /app/tests
