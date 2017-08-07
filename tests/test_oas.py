import os.path
import ruamel.yaml as yaml
from swagger_spec_validator.validator20 import validate_spec

HERE = os.path.dirname(__file__)


def test_oas_spec():
    with open(os.path.join(HERE, "..", "pollbot", "api.yaml"), 'r') as stream:
        oas_spec = yaml.load(stream)
    # example for swagger spec v2.0
    validate_spec(oas_spec)
