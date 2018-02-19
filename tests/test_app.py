import os
import pytest
from pollbot.app import get_app


def test_get_app_fails_if_telemetry_user_id_is_not_defined():
    initial_telemetry_user_value = os.getenv("TELEMETRY_USER_ID")
    try:
        os.environ["TELEMETRY_USER_ID"] = ""
        get_app()
    except SystemExit as e:
        assert e.code == 1
    else:
        pytest.fail("get_app did not raise")
    finally:
        os.environ["TELEMETRY_USER_ID"] = initial_telemetry_user_value


def test_get_app_fails_if_telemetry_user_id_is_not_a_integer():
    initial_telemetry_user_value = os.getenv("TELEMETRY_USER_ID")
    try:
        os.environ["TELEMETRY_USER_ID"] = "unknown"
        get_app()
    except SystemExit as e:
        assert e.code == 1
    else:
        pytest.fail("get_app did not raise")
    finally:
        os.environ["TELEMETRY_USER_ID"] = initial_telemetry_user_value
