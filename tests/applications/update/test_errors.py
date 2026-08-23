"""Tests for the update use-case domain error GraphRebuildFailedError (task 7).

Pins the sub-cell surface: the error is importable from
swax.applications.update, is an Exception subclass, stores its keyword-only
reason, and cannot be constructed positionally.
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
