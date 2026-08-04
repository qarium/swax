"""Contract tests for the EndpointDiff entity.

These tests pin the public surface and signatures of EndpointDiff: import from
the facade, keyword-only construction, three accessible fields, and the
has_changes / changed_paths methods. They fail with ImportError until the module
and the facade re-export exist (task 1).
"""

import inspect

import pytest
from swax.openapi import EndpointDiff


class TestEndpointDiffContract:
    def test_endpoint_diff_is_importable_from_facade(self):
        assert isinstance(EndpointDiff, type)

    def test_endpoint_diff_is_keyword_only(self):
        with pytest.raises(TypeError):
            EndpointDiff(["/x"], [], {})

    def test_endpoint_diff_exposes_three_fields(self):
        diff = EndpointDiff(added=["/a"], removed=["/b"], modified={"/c": ["resp 200 changed"]})

        assert diff.added == ["/a"]
        assert diff.removed == ["/b"]
        assert diff.modified == {"/c": ["resp 200 changed"]}

    def test_has_changes_signature(self):
        signature = inspect.signature(EndpointDiff.has_changes)

        assert list(signature.parameters) == ["self"]
        assert signature.return_annotation is bool

    def test_changed_paths_signature(self):
        signature = inspect.signature(EndpointDiff.changed_paths)

        assert list(signature.parameters) == ["self"]
        assert signature.return_annotation == list[str]

    def test_methods_are_callable(self):
        diff = EndpointDiff(added=["/a"], removed=[], modified={})

        assert callable(diff.has_changes)
        assert callable(diff.changed_paths)
