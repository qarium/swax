"""Domain error entity for the openapi cell.

SpecParseError wraps any Prance failure with the offending spec path and the
original reason, both exposed as public attributes (exc.path, exc.reason) so the
CLI handler can render a readable message without leaking anything sensitive.
"""

import pathlib


class SpecParseError(Exception):
    """Raised by parse_spec when parsing or dereferencing a spec fails.

    Args:
        path: offending spec file path.
        reason: original error message from Prance.
    """

    def __init__(self, *, path: pathlib.Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"path={path!r}, reason={reason!r}")


__all__: list[str] = [
    "SpecParseError",
]
