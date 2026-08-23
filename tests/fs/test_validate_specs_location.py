"""Tests for validate_specs_location — the mirroring path guard.

Covers acceptance of strictly-inside locations (including a child of
.swax/) and refusal of the project root, its ancestors, the .swax/
directory itself, outside directories, and parent-escaping relative paths.
"""

import pytest
from swax.fs import UnsafeSpecsLocationError, validate_specs_location


class TestValidateSpecsLocation:
    def test_validate_specs_location_accepts_nested_specs_dir(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()

        result = validate_specs_location(project_root=tmp_path, specs_location=specs)

        assert result is None

    def test_validate_specs_location_rejects_project_root(self, tmp_path):
        with pytest.raises(UnsafeSpecsLocationError) as exc_info:
            validate_specs_location(project_root=tmp_path, specs_location=tmp_path)

        assert exc_info.value.path == tmp_path

    def test_validate_specs_location_rejects_ancestor(self, tmp_path):
        ancestor = tmp_path.parent

        with pytest.raises(UnsafeSpecsLocationError) as exc_info:
            validate_specs_location(project_root=tmp_path, specs_location=ancestor)

        assert exc_info.value.path == ancestor

    def test_validate_specs_location_rejects_swax_dir(self, tmp_path):
        # Mirroring into .swax/ would delete config.yml and the traceability
        # graph together with the mirrored specs — the same destruction the
        # project-root refusal exists to prevent.
        swax_dir = tmp_path / ".swax"
        swax_dir.mkdir()

        with pytest.raises(UnsafeSpecsLocationError) as exc_info:
            validate_specs_location(project_root=tmp_path, specs_location=swax_dir)

        assert exc_info.value.path == swax_dir

    def test_validate_specs_location_accepts_specs_inside_swax_dir(self, tmp_path):
        # A child of .swax/ replaces only itself — config.yml and the graph
        # live one level above it and stay untouched.
        nested = tmp_path / ".swax" / "specs"
        nested.mkdir(parents=True)

        result = validate_specs_location(project_root=tmp_path, specs_location=nested)

        assert result is None

    def test_validate_specs_location_rejects_outside_directory(self, tmp_path):
        # The swap replaces the whole target directory, and swax must not
        # delete a directory it does not own — a sibling project (or any
        # absolute location) is refused like the project root itself.
        sibling = tmp_path.parent / "other-project"
        sibling.mkdir()

        with pytest.raises(UnsafeSpecsLocationError) as exc_info:
            validate_specs_location(project_root=tmp_path, specs_location=sibling)

        assert exc_info.value.path == sibling

    def test_validate_specs_location_rejects_parent_escape(self, tmp_path):
        # A relative location with enough ../ segments resolves outside the
        # project even though the configured string looks harmless.
        escaped = tmp_path / ".." / ".." / "elsewhere"

        with pytest.raises(UnsafeSpecsLocationError) as exc_info:
            validate_specs_location(project_root=tmp_path, specs_location=escaped)

        assert exc_info.value.path == escaped
