"""Logic tests for the OpenAIAdapter transport.

All tests inject a mock SDK client (mocker.MagicMock(spec=OpenAI)) — no live
OpenAI API is contacted. They cover first-choice content extraction (incl. the
None -> "" fallback), the exact messages list handed to chat.completions.create
(system prepended in both methods), the two error mappings (RateLimitError ->
LLMRateLimitedError, APIError -> LLMCallError), and multi-turn system-message
prepending.
"""

import httpx
import pytest
from openai import APIError, OpenAI, RateLimitError
from swax.llm import LLMCallError, LLMRateLimitedError, OpenAIAdapter
from swax.llm.OpenAIAdapter import DEFAULT_MODEL


def _mock_response(mocker, content):
    """Build a mock OpenAI chat completion response with the given content."""
    response = mocker.MagicMock()
    response.choices[0].message.content = content
    return response


def _rate_limit_error(message: str = "rate limited") -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError(message, response=response, body=None)


def _api_error(message: str = "api boom") -> APIError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return APIError(message, request=request, body=None)


class TestOpenAIAdapterAsk:
    def test_ask_returns_first_choice_content(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, "hello")
        adapter = OpenAIAdapter(client=sdk_client)

        result = adapter.ask(system="sys", user="hi")

        assert result == "hello"

    def test_ask_returns_empty_string_when_no_content(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, None)
        adapter = OpenAIAdapter(client=sdk_client)

        assert adapter.ask(system="sys", user="hi") == ""

    def test_ask_prepends_system_message(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, "")
        adapter = OpenAIAdapter(client=sdk_client)

        adapter.ask(system="system prompt", user="user payload")

        sdk_client.chat.completions.create.assert_called_once_with(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user payload"},
            ],
        )

    @pytest.mark.parametrize(
        ("error_factory", "expected"),
        [
            (lambda: _rate_limit_error("too many requests"), LLMRateLimitedError),
            (lambda: _api_error("internal error"), LLMCallError),
        ],
        ids=["rate_limit", "api"],
    )
    def test_ask_maps_rate_limit_and_api_errors(self, mocker, error_factory, expected):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.side_effect = error_factory()
        adapter = OpenAIAdapter(client=sdk_client)

        with pytest.raises(expected):
            adapter.ask(system="sys", user="hi")

    def test_ask_rate_limit_takes_precedence_over_api_error(self, mocker):
        # RateLimitError subclasses APIError in the SDK, so it must be caught first.
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.side_effect = _rate_limit_error()
        adapter = OpenAIAdapter(client=sdk_client)

        with pytest.raises(LLMRateLimitedError):
            adapter.ask(system="sys", user="hi")

    def test_ask_preserves_cause_on_mapped_error(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        original = _api_error("internal error")
        sdk_client.chat.completions.create.side_effect = original
        adapter = OpenAIAdapter(client=sdk_client)

        with pytest.raises(LLMCallError) as exc_info:
            adapter.ask(system="sys", user="hi")

        assert exc_info.value.__cause__ is original


class TestOpenAIAdapterAskMultiTurn:
    def test_ask_multi_turn_prepends_system_to_history(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, "")
        adapter = OpenAIAdapter(client=sdk_client)

        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second"},
        ]

        adapter.ask_multi_turn(system="sys", messages=history)

        sdk_client.chat.completions.create.assert_called_once_with(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "reply"},
                {"role": "user", "content": "second"},
            ],
        )

    def test_ask_multi_turn_returns_first_choice_content(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, "refined graph")
        adapter = OpenAIAdapter(client=sdk_client)

        result = adapter.ask_multi_turn(system="sys", messages=[{"role": "user", "content": "x"}])

        assert result == "refined graph"

    def test_ask_multi_turn_returns_empty_string_when_no_content(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, None)
        adapter = OpenAIAdapter(client=sdk_client)

        assert adapter.ask_multi_turn(system="sys", messages=[{"role": "user", "content": "x"}]) == ""

    def test_ask_multi_turn_maps_errors_like_ask(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.side_effect = _api_error("boom")
        adapter = OpenAIAdapter(client=sdk_client)

        with pytest.raises(LLMCallError):
            adapter.ask_multi_turn(system="sys", messages=[])

    def test_ask_multi_turn_preserves_message_order_and_identities(self, mocker):
        # The provided history list itself must not be mutated in place; the
        # prepended system message only appears in the call kwargs.
        sdk_client = mocker.MagicMock(spec=OpenAI)
        sdk_client.chat.completions.create.return_value = _mock_response(mocker, "")
        adapter = OpenAIAdapter(client=sdk_client)

        history = [{"role": "user", "content": "only"}]

        adapter.ask_multi_turn(system="sys", messages=history)

        assert history == [{"role": "user", "content": "only"}]


class TestOpenAIAdapterClientProperty:
    def test_client_property_returns_injected_instance(self, mocker):
        sdk_client = mocker.MagicMock(spec=OpenAI)

        adapter = OpenAIAdapter(client=sdk_client)

        assert adapter.client is sdk_client
