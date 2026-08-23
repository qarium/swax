"""Domain error entities for the fs cell.

The error is a keyword-only Exception subclass. It stores its contract field
as a public attribute (exc.path) and exposes a deterministic string form so
the CLI handler can surface the refused location to the user without leaking
anything sensitive — the same shape as the git cell errors.
"""

import pathlib


class UnsafeSpecsLocationError(Exception):
    """Raised by validate_specs_location when mirroring would target the project root or its ancestor.

    Args:
        path: the refused location.
    """

    def __init__(self, *, path: pathlib.Path) -> None:
        self.path = path
        super().__init__(f"path={path!r}")


__all__: list[str] = [
    "UnsafeSpecsLocationError",
]
