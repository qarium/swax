"""Atomic persistence of the traceability graph.

save_traceability_atomically writes the graph through save_traceability into
a temporary file next to the destination, then swaps it into place with a
single os.replace — the destination is never seen partially written. A failed
write removes the temporary file and re-raises, leaving the previous
destination untouched. Serialization semantics stay entirely with
save_traceability — no format changes here.
"""

import pathlib

from ...traceability import TraceabilityGraph, save_traceability


def save_traceability_atomically(graph: TraceabilityGraph, path: pathlib.Path) -> None:
    """Persist a TraceabilityGraph so the previous file survives a failed write.

    Algorithm:
    1. Serialize via save_traceability into ``{path.name}.tmp`` next to path.
    2. Replace path with the temporary file via Path.replace (os.replace —
       same-directory rename, one uninterrupted operation).
    3. On any failure remove the temporary file and let the error propagate.

    Args:
        graph: graph to write, deduplicated by the caller.
        path: destination file path (.swax/traceability.yml).
    """
    tmp_path = path.with_name(f"{path.name}.tmp")

    try:
        save_traceability(graph, tmp_path)

        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)

        raise


__all__: list[str] = [
    "save_traceability_atomically",
]
