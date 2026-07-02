"""Logic tests for the swax.fs cell.

Covers ensure_swax_dir (idempotent .swax/ creation) and copy_specs (merging
into existing destinations, parent directory creation, symlink handling).
All filesystem operations use the tmp_path fixture exclusively.
"""

from swax.fs import copy_specs, ensure_swax_dir


class TestEnsureSwaxDir:
    def test_ensure_swax_dir_creates_directory_idempotent(self, tmp_path):
        first = ensure_swax_dir(tmp_path)

        assert first == tmp_path / ".swax"
        assert first.is_dir()

        # second call is a no-op (idempotent — safe before every write)
        second = ensure_swax_dir(tmp_path)

        assert second == first


class TestCopySpecs:
    def test_copy_specs_merges_into_existing(self, tmp_path):
        source = tmp_path / "src"
        destination = tmp_path / "dst"
        source.mkdir()
        destination.mkdir()
        (source / "a.yaml").write_text("a: 1\n", encoding="utf-8")
        (destination / "b.yaml").write_text("b: 2\n", encoding="utf-8")

        copy_specs(source, destination)

        assert (destination / "a.yaml").exists()
        assert (destination / "b.yaml").exists()

    def test_copy_specs_creates_destination_parent(self, tmp_path):
        source = tmp_path / "src"
        destination = tmp_path / "nested" / "dst"
        source.mkdir()
        (source / "a.yaml").write_text("a: 1\n", encoding="utf-8")

        assert not destination.parent.exists()

        copy_specs(source, destination)

        assert destination.exists()
        assert (destination / "a.yaml").exists()

    def test_copy_specs_treats_symlinks_as_regular_files(self, tmp_path):
        source = tmp_path / "src"
        destination = tmp_path / "dst"
        source.mkdir()
        (source / "real.yaml").write_text("value: 1\n", encoding="utf-8")
        (source / "link.yaml").symlink_to(source / "real.yaml")

        copy_specs(source, destination)

        copied_link = destination / "link.yaml"
        assert copied_link.exists()
        assert not copied_link.is_symlink()
        assert copied_link.read_text(encoding="utf-8") == "value: 1\n"
