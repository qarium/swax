"""Domain error entities for the llm cell.

All four errors are keyword-only ``Exception`` subclasses. They store their
contract fields as public attributes (exc.reason, exc.excerpt, exc.protocol)
and never carry SWAX_LLM_TOKEN, so they are safe to surface in CLI output.
"""

__all__: list[str] = [
    "LLMCallError",
    "LLMRateLimitedError",
    "LLMResponseParseError",
    "UnsupportedLLMProtocolError",
]


class LLMCallError(Exception):
    """Raised by adapters on a generic (non-rate-limit) LLM API error.

    Args:
        reason: original error message from the SDK.
    """

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(f"reason={reason!r}")


class LLMRateLimitedError(Exception):
    """Raised by adapters when the LLM API returns a rate-limit error.

    Args:
        reason: original error message from the SDK.
    """

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(f"reason={reason!r}")


class LLMResponseParseError(Exception):
    """Raised by LLM consumers when defensive JSON parsing of a response fails.

    Args:
        reason: short diagnostic reason (e.g. "JSONDecodeError", "not a dict", "shape mismatch").
        excerpt: raw payload excerpt (first 200 chars) for diagnostics; never contains credentials.
    """

    def __init__(self, *, reason: str, excerpt: str) -> None:
        self.reason = reason
        self.excerpt = excerpt
        super().__init__(f"reason={reason!r}, excerpt={excerpt!r}")


class UnsupportedLLMProtocolError(Exception):
    """Raised by build_llm_client on an unknown SWAX_LLM_PROTOCOL value.

    Args:
        protocol: offending value submitted by the user.
    """

    def __init__(self, *, protocol: str) -> None:
        self.protocol = protocol
        super().__init__(f"protocol={protocol!r}")
