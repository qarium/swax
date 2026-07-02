"""Anthropic SDK adapter implementing the LLMClient transport contract.

The adapter wraps an injected Anthropic SDK client and exposes the two-method
LLMClient surface (ask / ask_multi_turn). It never stores SWAX_LLM_TOKEN (the
SDK client owns the credential) and maps SDK errors onto the domain error
entities so consumers stay provider-agnostic. DEFAULT_MODEL is pinned in code,
not the environment.
"""

from anthropic import Anthropic, APIError, RateLimitError

from .errors import LLMCallError, LLMRateLimitedError

DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicAdapter:
    """LLMClient transport backed by the Anthropic SDK.

    Args:
        client: injected Anthropic SDK client (constructed by build_anthropic_client).
    """

    def __init__(self, *, client: Anthropic) -> None:
        self._client = client

    @property
    def client(self) -> Anthropic:
        """The injected Anthropic SDK client instance."""
        return self._client

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
                model=DEFAULT_MODEL,
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
                model=DEFAULT_MODEL,
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
