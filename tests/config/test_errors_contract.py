"""Contract tests for the swax.config error entities.

These tests pin the public surface and the kw_only contract of
MissingEnvironmentVariablesError, InvalidLLMProtocolError, and
InvalidLLMBaseURLError. They fail with ImportError until the entities and
their facade re-exports exist (task 3).
"""

import pytest
from swax.config import (
    InvalidLLMBaseURLError,
    InvalidLLMProtocolError,
    MissingEnvironmentVariablesError,
)


class TestErrorsContract:
    def test_errors_are_importable_from_facade(self):
        assert MissingEnvironmentVariablesError is not None
        assert InvalidLLMProtocolError is not None
        assert InvalidLLMBaseURLError is not None

    def test_all_errors_subclass_exception(self):
        assert issubclass(MissingEnvironmentVariablesError, Exception)
        assert issubclass(InvalidLLMProtocolError, Exception)
        assert issubclass(InvalidLLMBaseURLError, Exception)

    def test_missing_env_error_stores_missing_attribute(self):
        exc = MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"])

        assert exc.missing == ["SWAX_LLM_TOKEN"]

    def test_missing_env_error_requires_keyword_arg(self):
        with pytest.raises(TypeError):
            MissingEnvironmentVariablesError(["SWAX_LLM_TOKEN"])

    def test_invalid_protocol_error_stores_value_and_allowed(self):
        exc = InvalidLLMProtocolError(value="ftp", allowed=("anthropic", "openai"))

        assert exc.value == "ftp"
        assert exc.allowed == ("anthropic", "openai")

    def test_invalid_protocol_error_requires_keyword_args(self):
        with pytest.raises(TypeError):
            InvalidLLMProtocolError("ftp", ("anthropic", "openai"))

    def test_invalid_base_url_error_stores_value_attribute(self):
        exc = InvalidLLMBaseURLError(value="https://example.com/v1")

        assert exc.value == "https://example.com/v1"

    def test_invalid_base_url_error_requires_keyword_arg(self):
        with pytest.raises(TypeError):
            InvalidLLMBaseURLError("https://example.com/v1")
