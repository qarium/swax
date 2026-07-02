"""Logic tests for the swax.llm protocol and error entities.

Covers field-storage fidelity and the string form of each error. The string
form is a regression guard: CLI handlers format these errors for users, so
the field values must appear in the human-readable representation, and the
token must never leak (these errors never carry SWAX_LLM_TOKEN).
"""

import inspect
import typing

import pytest
from swax.llm import (
    LLMCallError,
    LLMClient,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)


class TestLLMClientLogic:
    def test_llm_client_is_a_protocol_not_a_concrete_class(self):
        assert typing.Protocol in LLMClient.__mro__
        # structural typing only — adapters are not expected to inherit it
        assert LLMClient not in object.__subclasses__()

    def test_protocol_methods_have_no_implementation(self):
        # protocol methods declare a contract; the body is a bare ellipsis
        for method_name in ("ask", "ask_multi_turn"):
            method = getattr(LLMClient, method_name)
            source = inspect.getsource(method)
            # only the docstring and ellipsis, no real logic
            assert "..." in source


class TestLLMErrorsLogic:
    def test_all_errors_inherit_exception(self):
        for error_cls in (LLMCallError, LLMRateLimitedError, LLMResponseParseError, UnsupportedLLMProtocolError):
            assert issubclass(error_cls, Exception)
            assert not issubclass(error_cls, BaseException) or issubclass(error_cls, Exception)

    def test_response_parse_error_stores_both_fields(self):
        exc = LLMResponseParseError(reason="x", excerpt="y")

        assert exc.reason == "x"
        assert exc.excerpt == "y"

    def test_call_error_stores_reason(self):
        exc = LLMCallError(reason="timeout")

        assert exc.reason == "timeout"

    def test_rate_limited_error_stores_reason(self):
        exc = LLMRateLimitedError(reason="429 too many requests")

        assert exc.reason == "429 too many requests"

    def test_unsupported_protocol_error_stores_protocol(self):
        exc = UnsupportedLLMProtocolError(protocol="ftp")

        assert exc.protocol == "ftp"

    def test_call_error_string_includes_reason(self):
        exc = LLMCallError(reason="boom")

        assert "boom" in str(exc)

    def test_rate_limited_error_string_includes_reason(self):
        exc = LLMRateLimitedError(reason="slow down")

        assert "slow down" in str(exc)

    def test_response_parse_error_string_includes_reason_and_excerpt(self):
        exc = LLMResponseParseError(reason="not a dict", excerpt="{bad")

        text = str(exc)
        assert "not a dict" in text
        assert "{bad" in text

    def test_unsupported_protocol_error_string_includes_protocol(self):
        exc = UnsupportedLLMProtocolError(protocol="ftp")

        assert "ftp" in str(exc)

    def test_errors_are_raisable_and_catchable_individually(self):
        pairs = [
            (LLMCallError, {"reason": "a"}),
            (LLMRateLimitedError, {"reason": "b"}),
            (LLMResponseParseError, {"reason": "c", "excerpt": "d"}),
            (UnsupportedLLMProtocolError, {"protocol": "e"}),
        ]
        for cls, kwargs in pairs:
            with pytest.raises(cls) as exc_info:
                raise cls(**kwargs)
            for key, value in kwargs.items():
                assert getattr(exc_info.value, key) == value
