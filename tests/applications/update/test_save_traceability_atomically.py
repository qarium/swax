"""Tests for the cell-internal helper save_traceability_atomically (task 8).

Pins its module-level import path, its signature, its absence from the
facade, and the atomic-write behavior: the previous file survives a failed
write and the tmp file never leaks.
"""

import inspect
import pathlib

import pytest
import swax.applications.update as update_facade
from swax.applications.update.save_traceability_atomically import save_traceability_atomically
from swax.traceability import TraceabilityGraph


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
        assert "save_traceability_atomically" not in update_facade.__all__


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
