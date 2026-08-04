"""Reverse-reachability traversal over the traceability graph.

find_affected_endpoints takes the directly-changed endpoints and returns the
changed endpoints plus every endpoint that transitively depends on them. The
graph stores edges as ``source -> targets-it-depends-on`` (source depends on
target), so a node's dependents are the nodes whose adjacency list contains it.
The traversal is read-only — it never mutates the graph — and accepts plain path
strings so the cell stays free of any openapi import.
"""

from .traceability_graph import TraceabilityGraph


def find_affected_endpoints(
    changed_paths: list[str],
    graph: TraceabilityGraph,
) -> list[str]:
    """Return every endpoint transitively affected by the changed endpoints.

    Args:
        changed_paths: endpoints that changed directly (the directly-changed set
            supplied by the caller). These are always present in the result.
        graph: the loaded traceability graph.

    Returns:
        The changed endpoints plus every endpoint that transitively depends on
        them, sorted and deduplicated.

    The traversal walks the reverse adjacency (a node's dependents are the nodes
    whose adjacency list contains it). There is no internal cap — the complete
    closure is returned; the caller trims before the LLM call. The graph is not
    mutated.
    """
    affected: set[str] = set(changed_paths)

    # Build reverse adjacency from graph.edges: target -> sources that depend on it.
    reverse: dict[str, list[str]] = {}
    for source, targets in graph.edges.items():
        for target in targets:
            reverse.setdefault(target, []).append(source)

    queue: list[str] = list(changed_paths)
    while queue:
        node = queue.pop()
        for dependent in reverse.get(node, []):
            if dependent not in affected:
                affected.add(dependent)
                queue.append(dependent)

    return sorted(affected)


__all__: list[str] = [
    "find_affected_endpoints",
]
