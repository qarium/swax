"""Contract tests for the llm factory routines (task 15).

These tests pin the public surface: the three factory routines must be
importable from the facade with parameterless signatures and the documented
return annotations. They fail with ImportError until the facade re-exports the
factories.
"""

import inspect

from anthropic import Anthropic
from openai import OpenAI
from swax.llm import (
    LLMClient,
    build_anthropic_client,
    build_llm_client,
    build_openai_client,
)
from swax.llm import __all__ as llm_all


class TestBuildClientContract:
    def test_build_anthropic_client_is_importable_from_facade(self):
        assert callable(build_anthropic_client)

    def test_build_openai_client_is_importable_from_facade(self):
        assert callable(build_openai_client)

    def test_build_llm_client_is_importable_from_facade(self):
        assert callable(build_llm_client)

    def test_build_anthropic_client_takes_no_parameters(self):
        sig = inspect.signature(build_anthropic_client)

        assert list(sig.parameters) == []
        assert sig.return_annotation is Anthropic

    def test_build_openai_client_takes_no_parameters(self):
        sig = inspect.signature(build_openai_client)

        assert list(sig.parameters) == []
        assert sig.return_annotation is OpenAI

    def test_build_llm_client_takes_no_parameters(self):
        sig = inspect.signature(build_llm_client)

        assert list(sig.parameters) == []
        assert sig.return_annotation is LLMClient


class TestFacadeExposure:
    def test_facade_all_contains_all_ten_contract_names(self):
        expected = {
            "LLMClient",
            "AnthropicAdapter",
            "OpenAIAdapter",
            "LLMCallError",
            "LLMRateLimitedError",
            "LLMResponseParseError",
            "UnsupportedLLMProtocolError",
            "build_anthropic_client",
            "build_openai_client",
            "build_llm_client",
        }

        assert set(llm_all) == expected
