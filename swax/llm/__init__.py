"""Provider-agnostic LLM transport: protocol, adapters, and domain errors.

The facade is built incrementally. Task 12 exposed the LLMClient protocol and
the four error entities; task 13 added the AnthropicAdapter and task 14 adds the
OpenAIAdapter. The factory routines follow in task 15, at which point the full
surface is re-verified.
"""

from .AnthropicAdapter import AnthropicAdapter
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
]
