"""Contract tests for the AnthropicAdapter mutation entity.

These tests pin the public surface: the adapter must be importable from the
facade, constructed keyword-only with an injected SDK client and a model
identifier, expose both as read-only properties, and declare the two LLMClient
transport methods with the protocol-exact signatures.
"""

import inspect

import pytest
from anthropic import Anthropic
from swax.llm import AnthropicAdapter


class TestAnthropicAdapterContract:
    def test_adapter_is_importable_from_facade(self):
        assert AnthropicAdapter is not None

    def test_constructor_is_keyword_only(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        with pytest.raises(TypeError):
            AnthropicAdapter(sdk_client, model="claude-test")  # type: ignore[misc]

    def test_constructor_requires_model_kwarg(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        with pytest.raises(TypeError):
            AnthropicAdapter(client=sdk_client)  # type: ignore[call-arg]

    def test_constructor_accepts_client_and_model_keywords(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client, model="claude-test-model")

        assert isinstance(adapter, AnthropicAdapter)

    def test_client_is_a_property_returning_injected_client(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client, model="claude-test-model")

        assert isinstance(type(adapter).client, property)
        assert adapter.client is sdk_client

    def test_model_is_a_property_returning_injected_model(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client, model="claude-test-model")

        assert isinstance(type(adapter).model, property)
        assert adapter.model == "claude-test-model"

    def test_ask_signature_matches_protocol(self):
        sig = inspect.signature(AnthropicAdapter.ask)

        params = list(sig.parameters)
        assert params == ["self", "system", "user"]
        assert sig.parameters["system"].annotation is str
        assert sig.parameters["user"].annotation is str
        assert sig.return_annotation is str

    def test_ask_multi_turn_signature_matches_protocol(self):
        sig = inspect.signature(AnthropicAdapter.ask_multi_turn)

        params = list(sig.parameters)
        assert params == ["self", "system", "messages"]
        assert sig.parameters["system"].annotation is str
        assert sig.parameters["messages"].annotation == list[dict[str, str]]
        assert sig.return_annotation is str

    def test_adapter_satisfies_llm_client_protocol_structurally(self, mocker):
        # No inheritance is required: the adapter must expose both methods with
        # compatible signatures, satisfying LLMClient by duck typing.
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client, model="claude-test-model")

        assert callable(adapter.ask)
        assert callable(adapter.ask_multi_turn)
