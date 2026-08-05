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

    def test_classify_endpoint_changes_skips_components_added_and_removed(self):
        # The skip-components guarantee must hold for added/removed whole schemas
        # too (deepdiff dictionary_item_added/_removed), not only value changes.
        base = {"paths": {}, "components": {"schemas": {"Kept": {"name": "x"}}}}
        current = {
            "paths": {},
            "components": {"schemas": {"Kept": {"name": "x"}, "Orphan": {"name": "y"}}},
        }

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.added == []
        assert changes.removed == []
        assert changes.modified == {}
        assert changes.has_changes() is False

    def test_classify_endpoint_changes_detects_array_item_added(self):
        # deepdiff reports a list-element addition as iterable_item_added; it must
        # be classified as a modification of the owning endpoint (e.g. a new tag,
        # a new query parameter, or a new enum value).
        base = {"paths": {"/users": {"get": {"tags": ["users"]}}}}
        current = {"paths": {"/users": {"get": {"tags": ["users", "admin"]}}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert "/users" in changes.modified
        assert changes.added == []
        assert changes.removed == []
        assert changes.has_changes() is True

    def test_classify_endpoint_changes_detects_array_item_removed(self):
        # deepdiff reports a list-element removal as iterable_item_removed; it must
        # be classified as a modification (e.g. a removed parameter or enum value).
        base = {"paths": {"/users": {"get": {"parameters": [{"name": "a"}, {"name": "b"}]}}}}
        current = {"paths": {"/users": {"get": {"parameters": [{"name": "a"}]}}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert "/users" in changes.modified
        assert changes.added == []
        assert changes.removed == []
        assert changes.has_changes() is True

    def test_classify_endpoint_changes_deep_add_is_modification_not_added(self):
        # Adding a sub-field (here a new response code) to an endpoint that already
        # exists is a modification, not a new endpoint: only the two-segment path
        # ``root['paths']['<endpoint>']`` is a genuine endpoint add.
        base = {"paths": {"/users": {"get": {"responses": {"200": {"description": "ok"}}}}}}
        current = {
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "ok"},
                            "201": {"description": "created"},
                        },
                    },
                },
            },
        }

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.added == []
        assert changes.removed == []
        assert "/users" in changes.modified
        assert changes.has_changes() is True

    def test_classify_endpoint_changes_added_method_is_modification(self):
        # Adding a new method (post) to an existing endpoint is a modification,
        # not a new endpoint.
        base = {"paths": {"/users": {"get": {"responses": {"200": {"description": "ok"}}}}}}
        current = {
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "ok"}}},
                    "post": {"responses": {"201": {"description": "created"}}},
                },
            },
        }

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.added == []
        assert "/users" in changes.modified
        assert changes.has_changes() is True

    def test_classify_endpoint_changes_deep_remove_is_modification_not_removed(self):
        # Removing a sub-field from an existing endpoint is a modification, not a
        # removed endpoint — symmetric to the deep-add case.
        base = {
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "ok"},
                            "201": {"description": "created"},
                        },
                    },
                },
            },
        }
        current = {"paths": {"/users": {"get": {"responses": {"200": {"description": "ok"}}}}}}

        changes = classify_endpoint_changes(diff_specs(base, current))

        assert changes.removed == []
        assert changes.added == []
        assert "/users" in changes.modified
        assert changes.has_changes() is True
