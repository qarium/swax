"""Logic tests for the swax.config error entities.

Covers field storage fidelity and the string form of each error. The string
form is a regression guard: CLI handlers format these errors for users, so
the field values must appear in the human-readable representation.
"""

from swax.config import (
    InvalidLLMBaseURLError,
    InvalidLLMProtocolError,
    MissingEnvironmentVariablesError,
)


class TestErrorsLogic:
    def test_missing_env_error_keeps_missing_list(self):
        exc = MissingEnvironmentVariablesError(missing=["A"])

        assert exc.missing == ["A"]

    def test_invalid_protocol_error_keeps_value_and_allowed_tuple(self):
        exc = InvalidLLMProtocolError(value="ftp", allowed=("anthropic", "openai"))

        assert exc.value == "ftp"
        assert exc.allowed == ("anthropic", "openai")
        # tuple is preserved, not coerced to a list
        assert isinstance(exc.allowed, tuple)

    def test_invalid_base_url_error_keeps_value(self):
        exc = InvalidLLMBaseURLError(value="https://example.com/v1")

        assert exc.value == "https://example.com/v1"

    def test_missing_env_error_string_includes_value(self):
        exc = MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"])

        assert "SWAX_LLM_TOKEN" in str(exc)

    def test_invalid_protocol_error_string_includes_value_and_allowed(self):
        exc = InvalidLLMProtocolError(value="ftp", allowed=("anthropic", "openai"))

        text = str(exc)
        assert "ftp" in text
        assert "anthropic" in text
        assert "openai" in text

    def test_invalid_base_url_error_string_includes_value(self):
        exc = InvalidLLMBaseURLError(value="https://example.com/v1")

        assert "https://example.com/v1" in str(exc)
