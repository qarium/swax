"""Contract tests for the swax.traceability cell.

Pins the public surface: the TraceabilityGraph entity (kw_only constructor,
``add_edge`` / ``deduplicate`` / ``remove_paths`` methods, ``edges`` field)
and the load_traceability / save_traceability routine signatures. Fails with
ImportError until the modules and the facade re-exports exist (task 10).
"""

import inspect
import pathlib

import pytest
from swax.traceability import TraceabilityGraph, load_traceability, save_traceability


class TestTraceabilityContract:
    def test_entities_are_importable_from_facade(self):
        assert isinstance(TraceabilityGraph, type)
        assert callable(load_traceability)
        assert callable(save_traceability)

    def test_graph_has_add_edge_deduplicate_and_edges(self):
        assert callable(TraceabilityGraph.add_edge)
        assert callable(TraceabilityGraph.deduplicate)

        graph = TraceabilityGraph(edges={"/a": ["/b"]})
        assert graph.edges == {"/a": ["/b"]}

    def test_add_edge_signature(self):
        signature = inspect.signature(TraceabilityGraph.add_edge)

        assert list(signature.parameters) == ["self", "source", "target"]
        assert signature.parameters["source"].annotation is str
        assert signature.parameters["target"].annotation is str
        assert signature.return_annotation is None

    def test_deduplicate_signature(self):
        signature = inspect.signature(TraceabilityGraph.deduplicate)

        assert list(signature.parameters) == ["self"]
        assert signature.return_annotation is None

    def test_remove_paths_signature(self):
        signature = inspect.signature(TraceabilityGraph.remove_paths)

        assert list(signature.parameters) == ["self", "paths"]
        # list[str] is a generic alias — fresh object per evaluation, so
        # equality (not identity) is the comparable relation.
        assert signature.parameters["paths"].annotation == list[str]
        assert signature.return_annotation is None

    def test_load_traceability_signature(self):
        signature = inspect.signature(load_traceability)

        assert list(signature.parameters) == ["path"]
        assert signature.parameters["path"].annotation is pathlib.Path
        assert signature.return_annotation is TraceabilityGraph

    def test_save_traceability_signature(self):
        signature = inspect.signature(save_traceability)

        assert list(signature.parameters) == ["graph", "path"]
        assert signature.parameters["graph"].annotation is TraceabilityGraph
        assert signature.parameters["path"].annotation is pathlib.Path
        assert signature.return_annotation is None

    def test_graph_constructor_is_keyword_only(self):
        with pytest.raises(TypeError):
            TraceabilityGraph({"/a": ["/b"]})

    def test_graph_edges_default_empty(self):
        graph = TraceabilityGraph()

        assert graph.edges == {}
