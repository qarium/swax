"""Tests for the SpecsChanges value object.

Covers the predicates that drive every downstream branch of run_update:
has_changes (any list non-empty) and has_additions (added or updated
non-empty — the LLM-requiring branch selector, False for a removals-only
diff), plus the default-construction case.
"""

import pytest
from swax.fs import SpecsChanges


class TestSpecsChangesPredicates:
    @pytest.mark.parametrize(
        ("changes", "expected_has_changes", "expected_has_additions"),
        [
            pytest.param(SpecsChanges(added=[], updated=[], removed=[]), False, False, id="empty"),
            pytest.param(SpecsChanges(added=["a"]), True, True, id="added"),
            pytest.param(SpecsChanges(updated=["a"]), True, True, id="updated"),
            pytest.param(SpecsChanges(removed=["a"]), True, False, id="removed"),
        ],
    )
    def test_specs_changes_predicates(self, changes, expected_has_changes, expected_has_additions):
        assert changes.has_changes() is expected_has_changes
        assert changes.has_additions() is expected_has_additions

    def test_specs_changes_default_construction_reports_no_changes(self):
        changes = SpecsChanges()

        assert changes.has_changes() is False
        assert changes.has_additions() is False
