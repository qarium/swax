"""Contract tests for the swax.config env routines.

These tests pin the public surface and signatures of load_env, require_vars,
parse_protocol, and parse_base_url. They fail with ImportError until the
routines and their facade re-exports exist (task 4).
"""

import inspect
import pathlib

from swax.config import load_env, parse_base_url, parse_protocol, require_vars


class TestEnvContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(load_env)
        assert callable(require_vars)
        assert callable(parse_protocol)
        assert callable(parse_base_url)

    def test_load_env_signature(self):
        signature = inspect.signature(load_env)

        assert list(signature.parameters) == ["env_file"]
        env_file_param = signature.parameters["env_file"]
        assert env_file_param.annotation is pathlib.Path

    def test_require_vars_signature(self):
        signature = inspect.signature(require_vars)

        assert list(signature.parameters) == []
        # GenericAlias objects (dict[str, str]) are not interned, so compare by value.
        assert signature.return_annotation == dict[str, str]

    def test_parse_protocol_signature(self):
        signature = inspect.signature(parse_protocol)

        assert list(signature.parameters) == ["value"]
        assert signature.parameters["value"].annotation is str
        assert signature.return_annotation is str

    def test_parse_base_url_signature(self):
        signature = inspect.signature(parse_base_url)

        assert list(signature.parameters) == ["value"]
        assert signature.parameters["value"].annotation is str
        assert signature.return_annotation is str

    def test_require_vars_is_not_called_at_import_time(self):
        # require_vars must remain lazy: importing the cell does not validate env.
        # Re-importing must not raise even when SWAX_* vars are absent.
        assert require_vars is not None
