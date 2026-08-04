"""Logic tests for find_affected_endpoints and TraceabilityGraphMissingError.

Covers the reverse-reachability traversal (design-doc verbatim cases): the full
transitive closure over a small graph, a changed path absent from the graph
still being returned, read-only behavior (no mutation of graph.edges), and the
missing-graph error storing its path attribute.
"""

import pathlib

import pytest
from swax.traceability import (
    TraceabilityGraph,
    TraceabilityGraphMissingError,
    find_affected_endpoints,
)


class TestFindAffectedEndpointsLogic:
    def test_find_affected_endpoints_reverse_reachability(self):
        # /a depends on /b, /b depends on /c, /d depends on /c. Changing /c
        # transitively affects /a, /b, and /d (everything that reaches /c).
        graph = TraceabilityGraph(edges={"/a": ["/b"], "/b": ["/c"], "/d": ["/c"]})

        affected = find_affected_endpoints(["/c"], graph)

        assert affected == ["/a", "/b", "/c", "/d"]

    def test_find_affected_endpoints_keeps_changed_path_not_in_graph(self):
        # A changed path that is not a graph node is still returned as a seed;
        # its reverse lookup yields nothing.
        graph = TraceabilityGraph(edges={"/a": ["/b"]})

        affected = find_affected_endpoints(["/zzz"], graph)

        assert affected == ["/zzz"]

    def test_find_affected_endpoints_is_deduplicated_and_sorted(self):
        # Multiple changed paths and overlapping dependents collapse to a single
        # sorted, deduplicated list.
        graph = TraceabilityGraph(edges={"/a": ["/b"], "/c": ["/b"]})

        affected = find_affected_endpoints(["/b", "/b"], graph)

        assert affected == ["/a", "/b", "/c"]

    def test_find_affected_endpoints_is_read_only(self):
        graph = TraceabilityGraph(edges={"/a": ["/b"], "/b": ["/c"]})
        edges_before = {key: list(value) for key, value in graph.edges.items()}

        find_affected_endpoints(["/c"], graph)

        assert graph.edges == edges_before

    def test_find_affected_endpoints_empty_changes_returns_empty(self):
        graph = TraceabilityGraph(edges={"/a": ["/b"]})

        assert find_affected_endpoints([], graph) == []


class TestTraceabilityGraphMissingErrorLogic:
    def test_error_path_round_trip(self):
        path = pathlib.Path("x")

        error = TraceabilityGraphMissingError(path=path)

        assert error.path == pathlib.Path("x")

    def test_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            TraceabilityGraphMissingError(pathlib.Path("x"))  # type: ignore[misc]
