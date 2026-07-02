"""Factory: select the LLM adapter based on SWAX_LLM_PROTOCOL.

Reads SWAX_LLM_PROTOCOL from the environment and returns the matching adapter
wrapping its SDK client. Switching providers therefore needs no consumer code
change. An unknown protocol value raises UnsupportedLLMProtocolError.
"""

import os

from .AnthropicAdapter import AnthropicAdapter
from .build_anthropic_client import build_anthropic_client
from .build_openai_client import build_openai_client
from .errors import UnsupportedLLMProtocolError
from .LLMClient import LLMClient
from .OpenAIAdapter import OpenAIAdapter


def build_llm_client() -> LLMClient:
    """Build an LLMClient adapter selected by SWAX_LLM_PROTOCOL.

    Returns:
        An AnthropicAdapter or OpenAIAdapter wrapping the chosen SDK client.

    Raises:
        UnsupportedLLMProtocolError: when SWAX_LLM_PROTOCOL is neither
            "anthropic" nor "openai".
    """
    protocol = os.environ.get("SWAX_LLM_PROTOCOL")
    if protocol == "anthropic":
        return AnthropicAdapter(client=build_anthropic_client())
    if protocol == "openai":
        return OpenAIAdapter(client=build_openai_client())
    raise UnsupportedLLMProtocolError(protocol=protocol)


__all__: list[str] = ["build_llm_client"]
