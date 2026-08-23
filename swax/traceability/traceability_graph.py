"""TraceabilityGraph pydantic entity.

In-memory model of the traceability graph: a mapping of source path to its
dependent paths. The graph stores paths only — no HTTP methods, no resource
abstraction. Edges accumulate during run_discover via ``add_edge`` (duplicates
and self-loops permitted at insert time) and are resolved by ``deduplicate``
before deterministic serialization.
"""

from pydantic import BaseModel, ConfigDict, Field


class TraceabilityGraph(BaseModel):
    """Adjacency mapping of an API path to the paths it depends on.

    Args:
        edges: mapping of source path to its dependencies. Defaults to empty.
    """

    model_config = ConfigDict(kw_only=True)

    edges: dict[str, list[str]] = Field(default_factory=dict)

    def add_edge(self, source: str, target: str) -> None:
        """Record a single dependency: ``source`` depends on ``target``.

        Duplicates and self-loops (source == target) are permitted at insert
        time and resolved later by ``deduplicate``.

        Args:
            source: the path that gains a dependency.
            target: the path it now depends on.
        """
        self.edges.setdefault(source, []).append(target)

    def deduplicate(self) -> None:
        """Remove duplicate edges and self-loops in place.

        Each adjacency list is replaced by its sorted set and each source is
        removed from its own adjacency list. Sources left without any target
        are preserved — a path without dependencies remains a graph node. The
        operation is idempotent — calling it again produces no change.
        """
        for source in list(self.edges.keys()):
            self.edges[source] = sorted(set(self.edges[source]))
            if source in self.edges[source]:
                self.edges[source] = [target for target in self.edges[source] if target != source]

    def remove_paths(self, paths: list[str]) -> None:
        """Remove endpoints and every edge referencing them, in place.

        Algorithm:
        1. Drop every ``paths`` entry present as an adjacency key.
        2. Remove every ``paths`` entry from all remaining adjacency lists.

        Endpoints absent from the graph are ignored silently. Surviving keys
        and adjacency lists keep their relative order. Removal only — no new
        endpoints or edges are introduced. Persistence stays with the caller:
        invoke ``deduplicate`` before saving.

        Args:
            paths: endpoint paths to drop — API path templates extracted from
                spec files removed on the remote side, not file paths.
        """
        drop = set(paths)

        for key in list(self.edges.keys()):
            if key in drop:
                del self.edges[key]

        for source in self.edges:
            self.edges[source] = [target for target in self.edges[source] if target not in drop]


__all__: list[str] = [
    "TraceabilityGraph",
]
