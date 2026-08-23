"""Support-entity tests for the update use-case cell (tasks 7-9).

The contract-style first block pins the sub-cell surface: the domain error
GraphRebuildFailedError is importable from swax.applications.update, is an
Exception subclass, stores its keyword-only reason, and cannot be constructed
positionally. Later blocks (tasks 8-9) extend this file with the cell-internal
helpers save_traceability_atomically and render_update_summary.
"""

import pytest
from swax.applications.update import GraphRebuildFailedError


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
