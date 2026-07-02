"""Provider-agnostic LLM transport: protocol, adapters, and domain errors.

The facade is built incrementally. Task 12 exposed the LLMClient protocol and
the four error entities; task 13 added the AnthropicAdapter, task 14 added the
OpenAIAdapter, and task 15 adds the factory routines (build_anthropic_client,
build_openai_client, build_llm_client). The full nine-name surface is now
re-verified.
"""

from .AnthropicAdapter import AnthropicAdapter
from .build_anthropic_client import build_anthropic_client
from .build_llm_client import build_llm_client
from .build_openai_client import build_openai_client
from .errors import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from .LLMClient import LLMClient
from .OpenAIAdapter import OpenAIAdapter

__all__: list[str] = [
    "AnthropicAdapter",
    "LLMCallError",
    "LLMClient",
    "LLMRateLimitedError",
    "LLMResponseParseError",
    "OpenAIAdapter",
    "UnsupportedLLMProtocolError",
    "build_anthropic_client",
    "build_llm_client",
    "build_openai_client",
]
