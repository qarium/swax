"""Domain error entities for the config cell.

All three errors are keyword-only Exception subclasses. They store their
contract fields as public attributes (exc.missing, exc.value, exc.allowed)
and expose a deterministic string form so the CLI handlers can surface them
to users without leaking secrets (SWAX_LLM_TOKEN is never carried by these
errors).
"""


class MissingEnvironmentVariablesError(Exception):
    """Raised by require_vars when mandatory SWAX_* variables are missing.

    Args:
        missing: missing variable names, surfaced to the user.
    """

    def __init__(self, *, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"missing={missing!r}")


class InvalidLLMProtocolError(Exception):
    """Raised by parse_protocol on an unsupported SWAX_LLM_PROTOCOL value.

    Args:
        value: offending value submitted by the user.
        allowed: accepted protocol identifiers.
    """

    def __init__(self, *, value: str, allowed: tuple[str, ...]) -> None:
        self.value = value
        self.allowed = allowed
        super().__init__(f"value={value!r}, allowed={allowed!r}")


class InvalidLLMBaseURLError(Exception):
    """Raised by parse_base_url when SWAX_LLM_BASE_URL contains a version segment.

    Args:
        value: offending URL.
    """

    def __init__(self, *, value: str) -> None:
        self.value = value
        super().__init__(f"value={value!r}")


__all__: list[str] = [
    "InvalidLLMBaseURLError",
    "InvalidLLMProtocolError",
    "MissingEnvironmentVariablesError",
]
