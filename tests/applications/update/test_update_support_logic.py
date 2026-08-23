"""Support-entity tests for the update use-case cell (tasks 7-9).

The contract-style first block pins the sub-cell surface: the domain error
GraphRebuildFailedError is importable from swax.applications.update, is an
Exception subclass, stores its keyword-only reason, and cannot be constructed
positionally. The second block pins the cell-internal helper
save_traceability_atomically (task 8): its module-level import path, its
signature, and its absence from the facade. Later blocks (task 9) extend this
file with render_update_summary.
"""

import inspect
import pathlib

import pytest
from swax.applications.update import GraphRebuildFailedError
from swax.applications.update.save_traceability_atomically import save_traceability_atomically
from swax.traceability import TraceabilityGraph


class TestGraphRebuildFailedErrorContract:
    def test_importable_from_facade(self):
        assert callable(GraphRebuildFailedError)

    def test_is_exception_subclass(self):
        assert issubclass(GraphRebuildFailedError, Exception)

    def test_stores_reason(self):
        error = GraphRebuildFailedError(reason="boom")

        assert error.reason == "boom"

    def test_constructor_is_keyword_only(self):
        with pytest.raises(TypeError):
            GraphRebuildFailedError("boom")  # type: ignore[misc]


class TestSaveTraceabilityAtomicallyContract:
    def test_importable_from_internal_module(self):
        assert callable(save_traceability_atomically)

    def test_signature(self):
        signature = inspect.signature(save_traceability_atomically)

        params = list(signature.parameters)
        assert params == ["graph", "path"]
        assert signature.parameters["graph"].annotation is TraceabilityGraph
        assert signature.parameters["path"].annotation is pathlib.Path
        assert signature.return_annotation is None

    def test_not_exposed_on_facade(self):
        import swax.applications.update as facade

        assert "save_traceability_atomically" not in facade.__all__


class TestSaveTraceabilityAtomicallyLogic:
    def test_replaces_previous_file(self, tmp_path):
        swax_dir = tmp_path / ".swax"
        swax_dir.mkdir()
        path = swax_dir / "traceability.yml"
        path.write_text("old: content\n", encoding="utf-8")

        graph = TraceabilityGraph(edges={"/a": ["/b"]})

        save_traceability_atomically(graph, path)

        content = path.read_text(encoding="utf-8")
        assert "/a:" in content
        assert "- /b" in content
        assert "old" not in content
        assert not (swax_dir / ".traceability.yml.tmp").exists()

    def test_cleans_tmp_on_failure(self, tmp_path, mocker):
        swax_dir = tmp_path / ".swax"
        swax_dir.mkdir()
        path = swax_dir / "traceability.yml"
        old_content = "old: content\n"
        path.write_text(old_content, encoding="utf-8")

        mocker.patch(
            "swax.applications.update.save_traceability_atomically.save_traceability",
            side_effect=OSError("disk full"),
        )

        with pytest.raises(OSError, match="disk full"):
            save_traceability_atomically(TraceabilityGraph(edges={"/a": ["/b"]}), path)

        assert not (swax_dir / ".traceability.yml.tmp").exists()
        assert path.read_text(encoding="utf-8") == old_content
