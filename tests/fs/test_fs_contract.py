"""Contract tests for the swax.fs cell.

These tests pin the public surface and signatures of ensure_swax_dir,
copy_specs, and the spec-mirroring foundation entities (SpecsChanges,
UnsafeSpecsLocationError).
"""

import inspect
import pathlib

import pytest
from swax.fs import SpecsChanges, UnsafeSpecsLocationError, copy_specs, ensure_swax_dir


class TestFsContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(ensure_swax_dir)
        assert callable(copy_specs)

    def test_ensure_swax_dir_signature(self):
        signature = inspect.signature(ensure_swax_dir)

        assert list(signature.parameters) == ["project_root"]
        assert signature.parameters["project_root"].annotation is pathlib.Path
        assert signature.return_annotation is pathlib.Path

    def test_copy_specs_signature(self):
        signature = inspect.signature(copy_specs)

        assert list(signature.parameters) == ["source", "destination"]
        assert signature.parameters["source"].annotation is pathlib.Path
        assert signature.parameters["destination"].annotation is pathlib.Path


class TestSpecsChangesContract:
    def test_specs_changes_importable_from_facade(self):
        assert inspect.isclass(SpecsChanges)

    def test_specs_changes_constructor_is_keyword_only(self):
        with pytest.raises(TypeError):
            SpecsChanges(["a"])  # type: ignore[misc]

    def test_specs_changes_fields_default_to_empty_lists(self):
        changes = SpecsChanges()

        assert changes.added == []
        assert changes.updated == []
        assert changes.removed == []

    def test_specs_changes_field_annotations(self):
        fields = SpecsChanges.model_fields

        assert set(fields) == {"added", "updated", "removed"}
        # generic aliases are fresh objects per evaluation — compare by equality
        assert fields["added"].annotation == list[str]
        assert fields["updated"].annotation == list[str]
        assert fields["removed"].annotation == list[str]

    def test_has_changes_signature(self):
        signature = inspect.signature(SpecsChanges.has_changes)

        assert list(signature.parameters) == ["self"]
        assert signature.return_annotation is bool

    def test_has_additions_signature(self):
        signature = inspect.signature(SpecsChanges.has_additions)

        assert list(signature.parameters) == ["self"]
        assert signature.return_annotation is bool


class TestUnsafeSpecsLocationErrorContract:
    def test_unsafe_specs_location_error_importable_from_facade(self):
        assert inspect.isclass(UnsafeSpecsLocationError)

    def test_unsafe_specs_location_error_is_exception_subclass(self):
        assert issubclass(UnsafeSpecsLocationError, Exception)
