"""Structural protocol for provider-agnostic LLM transports.

Adapters (AnthropicAdapter, OpenAIAdapter) satisfy LLMClient implicitly via
duck typing — no inheritance is required and no runtime checks are performed
(no ``@runtime_checkable``). The protocol is domain-agnostic: methods accept
pre-built system/user strings and return raw response text. Multi-step
orchestration lives in the consumer, not here.
"""

from typing import Protocol


class LLMClient(Protocol):
    """Provider-agnostic LLM transport contract.

    Method signatures are the only thing consumers depend on, so provider
    switching requires no consumer code change.
    """

    def ask(self, system: str, user: str) -> str:
        """Single-turn transport: one system + one user message -> raw text."""
        ...

    def ask_multi_turn(self, system: str, messages: list[dict[str, str]]) -> str:
        """Multi-turn transport: system + ordered message history -> raw text."""
        ...


__all__: list[str] = ["LLMClient"]
