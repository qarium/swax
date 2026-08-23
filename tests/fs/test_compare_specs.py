"""Tests for compare_specs — byte-level classification of two specs trees.

Covers the added/updated/removed classification, the read-only guarantee, a
missing local root (everything added), and an empty remote root (everything
removed). All filesystem operations use tmp_path.
"""

from swax.fs import compare_specs


class TestCompareSpecs:
    def test_compare_specs_classifies_added_updated_removed(self, tmp_path):
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        local.mkdir()
        remote.mkdir()
        (local / "keep.yaml").write_text("same", encoding="utf-8")
        (remote / "keep.yaml").write_text("same", encoding="utf-8")
        (local / "changed.yaml").write_text("a", encoding="utf-8")
        (remote / "changed.yaml").write_text("b", encoding="utf-8")
        (local / "old.yaml").write_text("old", encoding="utf-8")
        (remote / "new.yaml").write_text("new", encoding="utf-8")

        changes = compare_specs(local_root=local, remote_root=remote)

        assert changes.added == ["new.yaml"]
        assert changes.updated == ["changed.yaml"]
        assert changes.removed == ["old.yaml"]
        assert changes.has_changes() is True
        assert changes.has_additions() is True
        # read-only guarantee — both trees keep their original bytes
        assert (local / "old.yaml").read_text(encoding="utf-8") == "old"
        assert (remote / "new.yaml").read_text(encoding="utf-8") == "new"

    def test_compare_specs_missing_local_root_classifies_all_remote_as_added(self, tmp_path):
        local = tmp_path / "local"  # never created
        remote = tmp_path / "remote"
        remote.mkdir()
        (remote / "a.yaml").write_text("a", encoding="utf-8")
        (remote / "sub").mkdir()
        (remote / "sub" / "b.yaml").write_text("b", encoding="utf-8")

        changes = compare_specs(local_root=local, remote_root=remote)

        assert changes.added == ["a.yaml", "sub/b.yaml"]
        assert changes.updated == []
        assert changes.removed == []
        assert changes.has_additions() is True

    def test_compare_specs_empty_remote_classifies_all_local_as_removed(self, tmp_path):
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        local.mkdir()
        remote.mkdir()
        (local / "a.yaml").write_text("a", encoding="utf-8")
        (local / "b.yaml").write_text("b", encoding="utf-8")

        changes = compare_specs(local_root=local, remote_root=remote)

        assert changes.removed == ["a.yaml", "b.yaml"]
        assert changes.added == []
        assert changes.updated == []
        assert changes.has_additions() is False
