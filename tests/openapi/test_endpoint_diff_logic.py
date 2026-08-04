"""Logic tests for the EndpointDiff entity.

Tests cover has_changes and changed_paths: deduplication of a path shared across
buckets, the empty-diff no-change short-circuit, and the sorted-union behavior.
"""

import pytest
from swax.openapi import EndpointDiff


class TestEndpointDiffChangedPaths:
    def test_changed_paths_dedup_across_buckets(self):
        # design-doc edge case test_endpoint_diff_changed_paths_dedup_across_buckets:
        # /x appears in both added and modified -> a single entry.
        diff_a = EndpointDiff(added=["/x"], removed=[], modified={"/x": ["resp 200 changed"]})

        assert diff_a.changed_paths() == ["/x"]
        assert diff_a.has_changes() is True

    def test_empty_diff_has_no_changes(self):
        # precondition no-change short-circuit (run_plan step 5).
        diff_b = EndpointDiff(added=[], removed=[], modified={})

        assert diff_b.has_changes() is False

    def test_changed_paths_sorted_union(self):
        diff = EndpointDiff(added=["/b", "/a"], removed=["/c"], modified={"/d": []})

        assert diff.changed_paths() == ["/a", "/b", "/c", "/d"]

    def test_changed_paths_deterministic_across_calls(self):
        diff = EndpointDiff(added=["/y", "/x"], removed=["/z"], modified={"/x": ["changed"]})

        first = diff.changed_paths()
        second = diff.changed_paths()

        assert first == second == ["/x", "/y", "/z"]


class TestEndpointDiffHasChanges:
    def test_has_changes_true_when_only_added(self):
        assert EndpointDiff(added=["/a"], removed=[], modified={}).has_changes() is True

    def test_has_changes_true_when_only_removed(self):
        assert EndpointDiff(added=[], removed=["/a"], modified={}).has_changes() is True

    def test_has_changes_true_when_only_modified(self):
        assert EndpointDiff(added=[], removed=[], modified={"/a": ["changed"]}).has_changes() is True

    def test_kw_only_enforced(self):
        with pytest.raises(TypeError):
            EndpointDiff(["/x"], [], {})
