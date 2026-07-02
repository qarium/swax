"""Logic tests for the AnthropicAdapter transport.

All tests inject a mock SDK client (mocker.MagicMock(spec=Anthropic)) — no live
Anthropic API is contacted. They cover text-block concatenation (filtering
non-text blocks), the exact kwargs handed to messages.create, the two error
mappings (RateLimitError -> LLMRateLimitedError, APIError -> LLMCallError), and
multi-turn message-order preservation.
"""

import httpx
import pytest
from anthropic import Anthropic, APIError, RateLimitError
from swax.llm import AnthropicAdapter, LLMCallError, LLMRateLimitedError
from swax.llm.AnthropicAdapter import DEFAULT_MODEL


def _text_block(mocker, text: str):
    block = mocker.MagicMock()
    block.type = "text"
    block.text = text
    return block


def _non_text_block(mocker, block_type: str = "tool_use"):
    block = mocker.MagicMock()
    block.type = block_type
    return block


def _rate_limit_error(message: str = "rate limited") -> RateLimitError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, request=request)
    return RateLimitError(message, response=response, body=None)


def _api_error(message: str = "api boom") -> APIError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return APIError(message, request=request, body=None)


class TestAnthropicAdapterAsk:
    def test_ask_returns_concatenated_text_blocks(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.return_value.content = [
            _text_block(mocker, "hello "),
            _text_block(mocker, "world"),
            _non_text_block(mocker),
        ]
        adapter = AnthropicAdapter(client=sdk_client)

        result = adapter.ask(system="sys", user="hi")

        assert result == "hello world"

    def test_ask_passes_system_and_user_to_sdk(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.return_value.content = []
        adapter = AnthropicAdapter(client=sdk_client)

        adapter.ask(system="system prompt", user="user payload")

        sdk_client.messages.create.assert_called_once_with(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system="system prompt",
            messages=[{"role": "user", "content": "user payload"}],
        )

    def test_ask_returns_empty_string_when_no_text_blocks(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.return_value.content = [_non_text_block(mocker)]
        adapter = AnthropicAdapter(client=sdk_client)

        assert adapter.ask(system="sys", user="hi") == ""

    def test_ask_maps_rate_limit_error(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.side_effect = _rate_limit_error("too many requests")
        adapter = AnthropicAdapter(client=sdk_client)

        with pytest.raises(LLMRateLimitedError) as exc_info:
            adapter.ask(system="sys", user="hi")

        assert "too many requests" in exc_info.value.reason

    def test_ask_maps_api_error(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.side_effect = _api_error("internal error")
        adapter = AnthropicAdapter(client=sdk_client)

        with pytest.raises(LLMCallError) as exc_info:
            adapter.ask(system="sys", user="hi")

        assert "internal error" in exc_info.value.reason

    def test_ask_rate_limit_takes_precedence_over_api_error(self, mocker):
        # RateLimitError subclasses APIError in the SDK, so it must be caught first.
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.side_effect = _rate_limit_error()
        adapter = AnthropicAdapter(client=sdk_client)

        with pytest.raises(LLMRateLimitedError):
            adapter.ask(system="sys", user="hi")

    def test_ask_preserves_cause_on_mapped_error(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        original = _api_error("internal error")
        sdk_client.messages.create.side_effect = original
        adapter = AnthropicAdapter(client=sdk_client)

        with pytest.raises(LLMCallError) as exc_info:
            adapter.ask(system="sys", user="hi")

        assert exc_info.value.__cause__ is original


class TestAnthropicAdapterAskMultiTurn:
    def test_ask_multi_turn_preserves_messages_order(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.return_value.content = [_text_block(mocker, "ok")]
        adapter = AnthropicAdapter(client=sdk_client)

        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second"},
        ]

        adapter.ask_multi_turn(system="sys", messages=history)

        sdk_client.messages.create.assert_called_once_with(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system="sys",
            messages=history,
        )

    def test_ask_multi_turn_returns_concatenated_text(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.return_value.content = [
            _text_block(mocker, "refined "),
            _text_block(mocker, "graph"),
        ]
        adapter = AnthropicAdapter(client=sdk_client)

        result = adapter.ask_multi_turn(system="sys", messages=[{"role": "user", "content": "x"}])

        assert result == "refined graph"

    def test_ask_multi_turn_maps_errors_like_ask(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)
        sdk_client.messages.create.side_effect = _api_error("boom")
        adapter = AnthropicAdapter(client=sdk_client)

        with pytest.raises(LLMCallError):
            adapter.ask_multi_turn(system="sys", messages=[])


class TestAnthropicAdapterClientProperty:
    def test_client_property_returns_injected_instance(self, mocker):
        sdk_client = mocker.MagicMock(spec=Anthropic)

        adapter = AnthropicAdapter(client=sdk_client)

        assert adapter.client is sdk_client
