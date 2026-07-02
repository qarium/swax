"""Provider-agnostic LLM transport: protocol, adapters, and domain errors.

The facade is built incrementally. Task 12 exposed the LLMClient protocol and
the four error entities; task 13 adds the AnthropicAdapter. The OpenAIAdapter
and the factory routines follow in tasks 14-15, at which point the full surface
is re-verified.
"""

from .AnthropicAdapter import AnthropicAdapter
from .errors import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from .LLMClient import LLMClient

__all__: list[str] = [
    "AnthropicAdapter",
    "LLMCallError",
    "LLMClient",
    "LLMRateLimitedError",
    "LLMResponseParseError",
    "UnsupportedLLMProtocolError",
]
