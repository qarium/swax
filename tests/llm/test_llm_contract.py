"""Contract tests for the swax.llm protocol and error entities.

These tests pin the public surface of task 12: the LLMClient structural
protocol and the four domain errors. They fail with ImportError until the
facade re-exports exist (task 12).
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


class TestLLMClientContract:
    def test_entities_are_importable_from_facade(self):
        assert LLMClient is not None
        assert LLMCallError is not None
        assert LLMRateLimitedError is not None
        assert LLMResponseParseError is not None
        assert UnsupportedLLMProtocolError is not None

    def test_llm_client_is_a_protocol(self):
        assert typing.Protocol in LLMClient.__mro__

    def test_llm_client_is_not_runtime_checkable(self):
        # No @runtime_checkable decorator: issubclass against the protocol
        # raises TypeError even for structurally-matching classes.
        class _StructuralMatch:
            def ask(self, system: str, user: str) -> str: ...

            def ask_multi_turn(self, system: str, messages: list[dict[str, str]]) -> str: ...

        with pytest.raises(TypeError):
            issubclass(_StructuralMatch, LLMClient)

    def test_llm_client_takes_no_constructor_parameters(self):
        # The contract is a structural protocol with no data: it declares only
        # the two transport methods and carries no fields/annotations. We verify
        # that the protocol body exposes no data attributes beyond the methods.
        declared = {name for name in LLMClient.__dict__ if not name.startswith("_")}
        assert declared == {"ask", "ask_multi_turn"}
        assert LLMClient.__annotations__ == {}

    def test_ask_signature_excludes_self(self):
        sig = inspect.signature(LLMClient.ask)

        params = [name for name in sig.parameters if name != "self"]
        assert params == ["system", "user"]
        assert sig.parameters["system"].annotation is str
        assert sig.parameters["user"].annotation is str
        assert sig.return_annotation is str

    def test_ask_multi_turn_signature_excludes_self(self):
        sig = inspect.signature(LLMClient.ask_multi_turn)

        params = [name for name in sig.parameters if name != "self"]
        assert params == ["system", "messages"]
        assert sig.parameters["system"].annotation is str
        assert sig.parameters["messages"].annotation == list[dict[str, str]]
        assert sig.return_annotation is str


class TestLLMErrorsContract:
    def test_all_errors_subclass_exception(self):
        assert issubclass(LLMCallError, Exception)
        assert issubclass(LLMRateLimitedError, Exception)
        assert issubclass(LLMResponseParseError, Exception)
        assert issubclass(UnsupportedLLMProtocolError, Exception)

    def test_errors_are_distinct_classes(self):
        classes = {LLMCallError, LLMRateLimitedError, LLMResponseParseError, UnsupportedLLMProtocolError}
        assert len(classes) == 4

    def test_call_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            LLMCallError("boom")  # type: ignore[misc]

    def test_rate_limited_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            LLMRateLimitedError("slow down")  # type: ignore[misc]

    def test_response_parse_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            LLMResponseParseError("bad", "{}")  # type: ignore[misc]

    def test_unsupported_protocol_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            UnsupportedLLMProtocolError("ftp")  # type: ignore[misc]

    def test_call_error_stores_reason(self):
        exc = LLMCallError(reason="boom")

        assert exc.reason == "boom"

    def test_rate_limited_error_stores_reason(self):
        exc = LLMRateLimitedError(reason="slow down")

        assert exc.reason == "slow down"

    def test_response_parse_error_stores_reason_and_excerpt(self):
        exc = LLMResponseParseError(reason="not a dict", excerpt="{}")

        assert exc.reason == "not a dict"
        assert exc.excerpt == "{}"

    def test_unsupported_protocol_error_stores_protocol(self):
        exc = UnsupportedLLMProtocolError(protocol="ftp")

        assert exc.protocol == "ftp"
