"""In-memory model and YAML persistence of the traceability graph.

The facade re-exports the TraceabilityGraph entity, the load_traceability /
save_traceability routines, the find_affected_endpoints reverse-reachability
traversal, and the TraceabilityGraphMissingError domain error. The graph stores
paths only — no HTTP methods, no resource abstraction. Edge deduplication is
mandatory before saving so the serialized output stays deterministic and
reviewable.
"""

from .errors import TraceabilityGraphMissingError
from .find_affected_endpoints import find_affected_endpoints
from .storage import load_traceability, save_traceability
from .traceability_graph import TraceabilityGraph

__all__: list[str] = [
    "TraceabilityGraph",
    "TraceabilityGraphMissingError",
    "find_affected_endpoints",
    "load_traceability",
    "save_traceability",
]
