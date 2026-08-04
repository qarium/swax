"""Domain error entity for the traceability cell.

TraceabilityGraphMissingError signals that .swax/traceability.yml does not exist
— the project has not run discover yet. The offending path is exposed as a
public attribute (exc.path) so the CLI handler can render a readable message and
point the user at swax discover. Raised by run_plan (existence check before
load_traceability), not by load_traceability itself.
"""

import pathlib


class TraceabilityGraphMissingError(Exception):
    """Raised when the traceability graph file does not exist.

    Args:
        path: expected location of .swax/traceability.yml.
    """

    def __init__(self, *, path: pathlib.Path) -> None:
        self.path = path
        super().__init__(f"path={path!r}")


__all__: list[str] = [
    "TraceabilityGraphMissingError",
]
