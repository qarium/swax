"""Provider-agnostic LLM transport: protocol and domain errors.

The facade is built incrementally. This task (12) exposes the LLMClient
protocol and the four error entities. The adapters (AnthropicAdapter,
OpenAIAdapter) and the factory routines are added in tasks 13-15, at which
point the full surface is re-verified.
"""

from .LLMClient import LLMClient
from .errors import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)

__all__: list[str] = [
    "LLMCallError",
    "LLMClient",
    "LLMRateLimitedError",
    "LLMResponseParseError",
    "UnsupportedLLMProtocolError",
]
