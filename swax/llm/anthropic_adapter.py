"""Anthropic SDK adapter implementing the LLMClient transport contract.

The adapter wraps an injected Anthropic SDK client and exposes the two-method
LLMClient surface (ask / ask_multi_turn). It never stores SWAX_LLM_TOKEN (the
SDK client owns the credential) and maps SDK errors onto the domain error
entities so consumers stay provider-agnostic. The model is injected via the
constructor — selected by build_llm_client from SWAX_LLM_MODEL.
"""

from anthropic import Anthropic, APIError, RateLimitError

from .errors import LLMCallError, LLMRateLimitedError


class AnthropicAdapter:
    """LLMClient transport backed by the Anthropic SDK.

    Args:
        client: injected Anthropic SDK client (constructed by build_anthropic_client).
        model: model identifier to send on every request (read from SWAX_LLM_MODEL
            by build_llm_client).
    """

    def __init__(self, *, client: Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def client(self) -> Anthropic:
        """The injected Anthropic SDK client instance."""
        return self._client

    @property
    def model(self) -> str:
        """The injected model identifier sent on every request."""
        return self._model

    def ask(self, system: str, user: str) -> str:
        """Single-turn Anthropic call: one system + one user message -> concatenated text.

        Args:
            system: system prompt (output of build_graph_system_prompt).
            user: user payload (output of a prompt builder).

        Returns:
            Concatenated text content blocks of the response.

        Raises:
            LLMRateLimitedError: when the Anthropic API returns a rate-limit error.
            LLMCallError: on any other Anthropic API error.
        """
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except RateLimitError as exc:
            raise LLMRateLimitedError(reason=str(exc)) from exc
        except APIError as exc:
            raise LLMCallError(reason=str(exc)) from exc

        return "".join(block.text for block in response.content if block.type == "text")

    def ask_multi_turn(self, system: str, messages: list[dict[str, str]]) -> str:
        """Multi-turn Anthropic call: system + ordered message history -> concatenated text.

        Args:
            system: system prompt reused across turns.
            messages: ordered list of {"role": ..., "content": ...} dicts for the refinement pass.

        Returns:
            Concatenated text content blocks of the response.

        Raises:
            LLMRateLimitedError: when the Anthropic API returns a rate-limit error.
            LLMCallError: on any other Anthropic API error.
        """
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=messages,
            )
        except RateLimitError as exc:
            raise LLMRateLimitedError(reason=str(exc)) from exc
        except APIError as exc:
            raise LLMCallError(reason=str(exc)) from exc

        return "".join(block.text for block in response.content if block.type == "text")


__all__: list[str] = ["AnthropicAdapter"]
