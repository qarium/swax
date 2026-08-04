"""Logic tests for the diff pipeline (diff_specs + classify_endpoint_changes).

These exercise behavior verbatim from the design-doc Test Stack Trace: an added
endpoint is detected and aggregated, a schema change is attributed to its
consuming endpoint (and no ``components`` / ``definitions`` path leaks), removed
endpoints and in-``paths`` value modifications are classified, and identical
specs yield no changes. DeepDiff is deterministic, so assertions are direct
(no mocking).
"""

from swax.openapi import classify_endpoint_changes, diff_specs


class TestDiffPipeline:
    def test_diff_specs_detects_added_endpoint(self):
        base = {"paths": {"/users": {}}}
        current = {"paths": {"/users": {}, "/orders": {}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.added == ["/orders"]
        assert changes.removed == []
        assert changes.modified == {}
        assert changes.has_changes() is True
        assert "/orders" in changes.changed_paths()

    def test_classify_endpoint_changes_detects_removed_endpoint(self):
        base = {"paths": {"/old": {}, "/users": {}}}
        current = {"paths": {"/users": {}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.removed == ["/old"]
        assert changes.added == []
        assert changes.modified == {}
        assert changes.has_changes() is True

    def test_classify_endpoint_changes_attributes_schema_change_to_endpoint(self):
        base = {
            "paths": {
                "/users": {"get": {"responses": {"200": {"schema": {"type": "object"}}}}},
            },
            "components": {"schemas": {"User": {"name": "old"}}},
        }
        current = {
            "paths": {
                "/users": {"get": {"responses": {"200": {"schema": {"type": "string"}}}}},
            },
            "components": {"schemas": {"User": {"name": "new"}}},
        }

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert "/users" in changes.modified
        assert all(ep.startswith("/") for ep in changes.modified)
        assert changes.added == []
        assert changes.removed == []

    def test_classify_endpoint_changes_modifies_value_under_paths(self):
        base = {"paths": {"/users": {"get": {"summary": "list users"}}}}
        current = {"paths": {"/users": {"get": {"summary": "list all users"}}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert "/users" in changes.modified
        assert len(changes.modified["/users"]) >= 1
        assert changes.added == []
        assert changes.removed == []
        assert changes.has_changes() is True

    def test_identical_specs_have_no_changes(self):
        spec = {"paths": {"/users": {"get": {"summary": "x"}}}}

        changes = classify_endpoint_changes(diff_specs(spec, spec))

        assert changes.added == []
        assert changes.removed == []
        assert changes.modified == {}
        assert changes.has_changes() is False
        assert changes.changed_paths() == []

    def test_classify_endpoint_changes_descriptions_are_sorted_and_deterministic(self):
        base = {
            "paths": {
                "/users": {
                    "get": {"summary": "a", "description": "b"},
                },
            },
        }
        current = {
            "paths": {
                "/users": {
                    "get": {"summary": "x", "description": "y"},
                },
            },
        }

        first = classify_endpoint_changes(diff_specs(base, current))
        second = classify_endpoint_changes(diff_specs(base, current))

        assert first.modified["/users"] == sorted(first.modified["/users"])
        assert first.modified == second.modified

    def test_classify_endpoint_changes_skips_components_and_definitions_only(self):
        # A schema change that no endpoint consumes must not surface any report path.
        base = {"paths": {}, "components": {"schemas": {"Orphan": {"name": "old"}}}}
        current = {"paths": {}, "components": {"schemas": {"Orphan": {"name": "new"}}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.added == []
        assert changes.removed == []
        assert changes.modified == {}
        assert changes.has_changes() is False
