"""Logic tests for the llm factory routines.

All tests isolate SWAX_LLM_* from the real environment (autouse fixture clears
them per test) and patch the SDK client constructors at their import point so
no real credential is needed and no SDK call is made. They cover the env-read
flow, the fail-fast ordering of require_vars, the per-protocol adapter
selection (incl. propagation of the model from SWAX_LLM_MODEL into the
adapter), and the unknown-protocol error.
"""

import pytest
from anthropic import Anthropic
from openai import OpenAI
from swax.config import MissingEnvironmentVariablesError
from swax.llm import (
    AnthropicAdapter,
    OpenAIAdapter,
    UnsupportedLLMProtocolError,
    build_anthropic_client,
    build_llm_client,
    build_openai_client,
)

_SWAX_VARS = ("SWAX_LLM_MODEL", "SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN")


@pytest.fixture(autouse=True)
def _clear_swax_env(monkeypatch):
    """Clear any SWAX_LLM_* leaked from the shell or a prior test."""
    for name in _SWAX_VARS:
        monkeypatch.delenv(name, raising=False)


class TestBuildAnthropicClient:
    def test_build_anthropic_client_reads_env(self, mocker, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "anthropic")
        monkeypatch.setenv("SWAX_LLM_BASE_URL", "https://api.example.com")
        monkeypatch.setenv("SWAX_LLM_TOKEN", "secret-token")
        monkeypatch.setenv("SWAX_LLM_MODEL", "claude-test-model")
        mock_anthropic = mocker.patch("swax.llm.build_anthropic_client.Anthropic")

        result = build_anthropic_client()

        mock_anthropic.assert_called_once_with(
            api_key="secret-token",
            base_url="https://api.example.com",
        )
        assert result is mock_anthropic.return_value

    def test_build_anthropic_client_calls_require_vars_first(self):
        # No SWAX_LLM_* in the environment -> require_vars fails before any
        # SDK client is constructed.
        with pytest.raises(MissingEnvironmentVariablesError):
            build_anthropic_client()


class TestBuildOpenAIClient:
    def test_build_openai_client_analogous(self, mocker, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "openai")
        monkeypatch.setenv("SWAX_LLM_BASE_URL", "https://api.openai.example")
        monkeypatch.setenv("SWAX_LLM_TOKEN", "openai-token")
        monkeypatch.setenv("SWAX_LLM_MODEL", "gpt-test-model")
        mock_openai = mocker.patch("swax.llm.build_openai_client.OpenAI")

        result = build_openai_client()

        mock_openai.assert_called_once_with(
            api_key="openai-token",
            base_url="https://api.openai.example",
        )
        assert result is mock_openai.return_value

    def test_build_openai_client_calls_require_vars_first(self):
        with pytest.raises(MissingEnvironmentVariablesError):
            build_openai_client()


class TestBuildLlmClient:
    def test_build_llm_client_returns_anthropic_adapter_with_model(self, mocker, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "anthropic")
        monkeypatch.setenv("SWAX_LLM_MODEL", "claude-test-model")
        mock_build = mocker.patch("swax.llm.build_llm_client.build_anthropic_client")
        mock_sdk_client = mocker.MagicMock(spec=Anthropic)
        mock_build.return_value = mock_sdk_client

        client = build_llm_client()

        mock_build.assert_called_once_with()
        assert isinstance(client, AnthropicAdapter)
        assert client.client is mock_sdk_client
        assert client.model == "claude-test-model"

    def test_build_llm_client_returns_openai_adapter_with_model(self, mocker, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "openai")
        monkeypatch.setenv("SWAX_LLM_MODEL", "gpt-test-model")
        mock_build = mocker.patch("swax.llm.build_llm_client.build_openai_client")
        mock_sdk_client = mocker.MagicMock(spec=OpenAI)
        mock_build.return_value = mock_sdk_client

        client = build_llm_client()

        mock_build.assert_called_once_with()
        assert isinstance(client, OpenAIAdapter)
        assert client.client is mock_sdk_client
        assert client.model == "gpt-test-model"

    def test_build_llm_client_raises_on_unknown_protocol(self, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "ftp")
        monkeypatch.setenv("SWAX_LLM_MODEL", "any")

        with pytest.raises(UnsupportedLLMProtocolError) as exc_info:
            build_llm_client()

        assert exc_info.value.protocol == "ftp"

    def test_build_llm_client_raises_when_protocol_unset(self):
        with pytest.raises(UnsupportedLLMProtocolError) as exc_info:
            build_llm_client()

        assert exc_info.value.protocol is None

    def test_build_llm_client_fails_fast_when_model_missing(self, mocker, monkeypatch):
        # require_vars (called inside build_*_client) must catch the missing
        # SWAX_LLM_MODEL before build_llm_client ever reads it from os.environ.
        monkeypatch.setenv("SWAX_LLM_PROTOCOL", "anthropic")
        monkeypatch.setenv("SWAX_LLM_BASE_URL", "https://api.example.com")
        monkeypatch.setenv("SWAX_LLM_TOKEN", "secret-token")
        # SWAX_LLM_MODEL intentionally unset.

        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            build_llm_client()

        assert "SWAX_LLM_MODEL" in exc_info.value.missing
