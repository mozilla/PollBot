#!/bin/bash
# Run tests in the docker image
python3 -m venv /tmp/tests
/tmp/tests/bin/pip install -r /app/dev-requirements.txt
/tmp/tests/bin/pip install /app
/tmp/tests/bin/py.test /app/tests
