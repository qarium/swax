"""Pure rendering of the update summary.

render_update_summary turns a SpecsChanges value object plus an optional graph
status line into the human-readable summary echoed by the update command.
It is a pure transformation: no I/O, no re-sorting (the paths arrive sorted
from compare_specs), no knowledge of how the changes were produced.
"""

from ...fs import SpecsChanges


def render_update_summary(changes: SpecsChanges, graph_status: str | None) -> str:
    """Render the update summary from classified changes and a graph status.

    Algorithm:
    1. Append the ``Added:`` / ``Updated:`` / ``Removed:`` group headers in
       that fixed order, each followed by one ``  - {path}`` line per path;
       empty groups are omitted entirely.
    2. Append ``Traceability graph: {graph_status}`` on its own line only
       when graph_status is not None.
    3. Join all lines with newlines.

    Args:
        changes: file-level classification produced by compare_specs; the
            lists are rendered in the given (already sorted) order.
        graph_status: outcome of the graph work ("rebuilt", "built") or None
            when no status line applies.

    Returns:
        output: the multi-line summary string.
    """
    lines: list[str] = []

    for title, paths in (
        ("Added:", changes.added),
        ("Updated:", changes.updated),
        ("Removed:", changes.removed),
    ):
        if not paths:
            continue

        lines.append(title)
        lines.extend(f"  - {path}" for path in paths)

    if graph_status is not None:
        lines.append(f"Traceability graph: {graph_status}")

    return "\n".join(lines)


__all__: list[str] = [
    "render_update_summary",
]
