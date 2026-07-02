"""OpenAI SDK adapter implementing the LLMClient transport contract.

The adapter wraps an injected OpenAI SDK client and exposes the two-method
LLMClient surface (ask / ask_multi_turn). It never stores SWAX_LLM_TOKEN (the
SDK client owns the credential) and maps SDK errors onto the domain error
entities so consumers stay provider-agnostic. DEFAULT_MODEL is pinned in code,
not the environment.
"""

from openai import APIError, OpenAI, RateLimitError

from .errors import LLMCallError, LLMRateLimitedError

DEFAULT_MODEL = "gpt-4o"


class OpenAIAdapter:
    """LLMClient transport backed by the OpenAI SDK.

    Args:
        client: injected OpenAI SDK client (constructed by build_openai_client).
    """

    def __init__(self, *, client: OpenAI) -> None:
        self._client = client

    @property
    def client(self) -> OpenAI:
        """The injected OpenAI SDK client instance."""
        return self._client

    def ask(self, system: str, user: str) -> str:
        """Single-turn OpenAI call: one system + one user message -> first choice content.

        Args:
            system: system prompt (output of build_graph_system_prompt).
            user: user payload (output of a prompt builder).

        Returns:
            The first choice message content, or an empty string when absent.

        Raises:
            LLMRateLimitedError: when the OpenAI API returns a rate-limit error.
            LLMCallError: on any other OpenAI API error.
        """
        try:
            response = self._client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except RateLimitError as exc:
            raise LLMRateLimitedError(reason=str(exc)) from exc
        except APIError as exc:
            raise LLMCallError(reason=str(exc)) from exc

        return response.choices[0].message.content or ""

    def ask_multi_turn(self, system: str, messages: list[dict[str, str]]) -> str:
        """Multi-turn OpenAI call: system + ordered message history -> first choice content.

        The system prompt is prepended to the provided message history so the
        refinement pass reuses the same system context as the first pass.

        Args:
            system: system prompt reused across turns.
            messages: ordered list of {"role": ..., "content": ...} dicts for the refinement pass.

        Returns:
            The first choice message content, or an empty string when absent.

        Raises:
            LLMRateLimitedError: when the OpenAI API returns a rate-limit error.
            LLMCallError: on any other OpenAI API error.
        """
        prepended = [{"role": "system", "content": system}, *messages]
        try:
            response = self._client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=prepended,
            )
        except RateLimitError as exc:
            raise LLMRateLimitedError(reason=str(exc)) from exc
        except APIError as exc:
            raise LLMCallError(reason=str(exc)) from exc

        return response.choices[0].message.content or ""


__all__: list[str] = ["OpenAIAdapter"]
