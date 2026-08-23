"""Tests for the cell-internal helper render_update_summary (task 9).

Pins its module-level import path, its signature, its absence from the
facade, and the pure rendering behavior: group order, empty-group omission,
and the optional status line.
"""

import inspect

import swax.applications.update as update_facade
from swax.applications.update.render_update_summary import render_update_summary
from swax.fs import SpecsChanges


class TestRenderUpdateSummaryContract:
    def test_importable_from_internal_module(self):
        assert callable(render_update_summary)

    def test_signature(self):
        signature = inspect.signature(render_update_summary)

        params = list(signature.parameters)
        assert params == ["changes", "graph_status"]
        assert signature.parameters["changes"].annotation is SpecsChanges
        assert signature.parameters["graph_status"].annotation == (str | None)
        assert signature.return_annotation is str

    def test_not_exposed_on_facade(self):
        assert "render_update_summary" not in update_facade.__all__


class TestRenderUpdateSummaryLogic:
    def test_groups_sorted_paths_and_status(self):
        changes = SpecsChanges(
            added=["orders.yaml"],
            updated=["a.yaml", "users.yaml"],
            removed=["legacy.yaml"],
        )

        output = render_update_summary(changes, graph_status="rebuilt")

        assert output == (
            "Added:\n"
            "  - orders.yaml\n"
            "Updated:\n"
            "  - a.yaml\n"
            "  - users.yaml\n"
            "Removed:\n"
            "  - legacy.yaml\n"
            "Traceability graph: rebuilt"
        )

    def test_omits_empty_groups_and_none_status(self):
        changes = SpecsChanges(added=[], updated=[], removed=["only.yaml"])

        output = render_update_summary(changes, graph_status=None)

        assert output == "Removed:\n  - only.yaml"
