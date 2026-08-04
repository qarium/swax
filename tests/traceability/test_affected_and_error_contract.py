"""Contract tests for find_affected_endpoints and TraceabilityGraphMissingError.

Pins the public surface and signatures of the two new traceability entities:
find_affected_endpoints (reverse-reachability traversal, read-only) and
TraceabilityGraphMissingError (keyword-only Exception carrying ``.path``).
Fails with ImportError until the modules and the facade re-exports exist (task 3).
"""

import inspect
import pathlib

import pytest
from swax.traceability import TraceabilityGraph, TraceabilityGraphMissingError, find_affected_endpoints


class TestAffectedEndpointsContract:
    def test_find_affected_endpoints_is_importable_from_facade(self):
        assert callable(find_affected_endpoints)

    def test_find_affected_endpoints_signature(self):
        signature = inspect.signature(find_affected_endpoints)

        assert list(signature.parameters) == ["changed_paths", "graph"]
        assert signature.parameters["changed_paths"].annotation == list[str]
        assert signature.parameters["graph"].annotation is TraceabilityGraph
        assert signature.return_annotation == list[str]

    def test_find_affected_endpoints_returns_list(self):
        graph = TraceabilityGraph(edges={"/a": ["/b"]})

        result = find_affected_endpoints(["/a"], graph)

        assert isinstance(result, list)


class TestTraceabilityGraphMissingErrorContract:
    def test_error_is_importable_from_facade(self):
        assert isinstance(TraceabilityGraphMissingError, type)
        assert issubclass(TraceabilityGraphMissingError, Exception)

    def test_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            TraceabilityGraphMissingError(pathlib.Path("x"))  # type: ignore[misc]

    def test_error_stores_path_attribute(self):
        path = pathlib.Path(".swax") / "traceability.yml"

        error = TraceabilityGraphMissingError(path=path)

        assert error.path == path

    def test_error_can_be_raised_and_caught(self):
        with pytest.raises(TraceabilityGraphMissingError) as info:
            raise TraceabilityGraphMissingError(path=pathlib.Path("missing.yml"))

        assert info.value.path == pathlib.Path("missing.yml")
