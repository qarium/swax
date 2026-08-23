"""Domain error entities for the update use-case cell.

The error is a keyword-only Exception subclass. It stores its contract field
as a public attribute (exc.reason) and exposes a deterministic string form —
the same shape as the git and fs cell errors.
"""


class GraphRebuildFailedError(Exception):
    """Raised by run_update when the graph rebuild after applying specs fails.

    The specs have been restored from the backup at that point — the error
    signals a failed rebuild over an already-rolled-back project state.

    Args:
        reason: short diagnostic reason carried from the underlying failure.
    """

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(f"reason={reason!r}")


__all__: list[str] = [
    "GraphRebuildFailedError",
]
