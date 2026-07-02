"""Contract tests for the AnthropicAdapter mutation entity.

These tests pin the public surface introduced in task 13: the adapter must be
importable from the facade, constructed keyword-only with an injected SDK
client, expose that client as a read-only property, and declare the two LLMClient
transport methods with the protocol-exact signatures. They fail with ImportError
until the facade re-exports AnthropicAdapter.
"""

import inspect

import pytest
from anthropic import Anthropic
from swax.llm import AnthropicAdapter
from swax.llm.AnthropicAdapter import DEFAULT_MODEL


class TestAnthropicAdapterContract:
    def test_adapter_is_importable_from_facade(self):
        assert AnthropicAdapter is not None

    def test_default_model_is_a_nonempty_string(self):
        # The model is pinned in code (not env) per the contract.
        assert isinstance(DEFAULT_MODEL, str)
        assert DEFAULT_MODEL.strip() != ""

    def test_constructor_is_keyword_only(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        with pytest.raises(TypeError):
            AnthropicAdapter(sdk_client)  # type: ignore[misc]

    def test_constructor_accepts_keyword_argument(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client)

        assert isinstance(adapter, AnthropicAdapter)

    def test_client_is_a_property_returning_injected_client(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client)

        assert isinstance(type(adapter).client, property)
        assert adapter.client is sdk_client

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

        adapter = AnthropicAdapter(client=sdk_client)

        assert callable(adapter.ask)
        assert callable(adapter.ask_multi_turn)
