"""In-memory model and YAML persistence of the traceability graph.

The facade re-exports the TraceabilityGraph entity and the load_traceability /
save_traceability routines. The graph stores paths only — no HTTP methods, no
resource abstraction. Edge deduplication is mandatory before saving so the
serialized output stays deterministic and reviewable.
"""

from .storage import load_traceability, save_traceability
from .traceability_graph import TraceabilityGraph

__all__: list[str] = [
    "TraceabilityGraph",
    "load_traceability",
    "save_traceability",
]
