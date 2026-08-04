"""Contract tests for the diff pipeline (diff_specs, classify_endpoint_changes).

These tests pin the public surface and signatures of the two routines: both are
importable from the facade, their parameter lists match the contract
(``diff_specs(base, current)`` and ``classify_endpoint_changes(diff)``), and
diff_specs returns a ``deepdiff.DeepDiff``. They fail with ImportError until the
modules and the facade re-exports exist (task 2).
"""

import inspect

from deepdiff import DeepDiff
from swax.openapi import EndpointDiff, classify_endpoint_changes, diff_specs


class TestDiffContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(diff_specs)
        assert callable(classify_endpoint_changes)

    def test_diff_specs_signature(self):
        signature = inspect.signature(diff_specs)

        assert list(signature.parameters) == ["base", "current"]
        assert signature.return_annotation is DeepDiff

    def test_classify_endpoint_changes_signature(self):
        signature = inspect.signature(classify_endpoint_changes)

        assert list(signature.parameters) == ["diff"]
        assert signature.return_annotation is EndpointDiff

    def test_diff_specs_returns_deepdiff(self):
        result = diff_specs({"paths": {}}, {"paths": {}})

        assert isinstance(result, DeepDiff)

    def test_classify_endpoint_changes_returns_endpoint_diff(self):
        result = classify_endpoint_changes(diff_specs({"paths": {}}, {"paths": {}}))

        assert isinstance(result, EndpointDiff)
