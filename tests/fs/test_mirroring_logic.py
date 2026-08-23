"""Logic tests for the swax.fs spec-mirroring entities.

Covers the SpecsChanges predicates that drive every downstream branch of
run_update (has_changes: any list non-empty; has_additions: added or updated
non-empty — the LLM-requiring branch selector, False for a removals-only
diff), the byte-level tree classification of compare_specs, the mirroring
path guard validate_specs_location, and the transactional directory
replacement staged_specs_swap.
"""

import pytest
from swax.fs import (
    SpecsChanges,
    UnsafeSpecsLocationError,
    compare_specs,
    staged_specs_swap,
    validate_specs_location,
)


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


class TestStagedSpecsSwap:
    def test_staged_specs_swap_replaces_target_and_removes_backup(self, tmp_path):
        target = tmp_path / "target"
        staging = tmp_path / "staging"
        target.mkdir()
        staging.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        (staging / "new.txt").write_text("new", encoding="utf-8")

        with staged_specs_swap(target=target, staging=staging) as live_root:
            assert (live_root / "new.txt").read_text(encoding="utf-8") == "new"
            assert not (live_root / "old.txt").exists()

        assert target.is_dir()
        assert (target / "new.txt").exists()
        assert not (tmp_path / ".target.backup").exists()
        assert not staging.exists()

    def test_staged_specs_swap_restores_target_on_exception(self, tmp_path):
        target = tmp_path / "target"
        staging = tmp_path / "staging"
        target.mkdir()
        staging.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        (staging / "new.txt").write_text("new", encoding="utf-8")

        with pytest.raises(RuntimeError), staged_specs_swap(target=target, staging=staging):
            raise RuntimeError("graph rebuild failed")

        assert (target / "old.txt").exists()
        assert not (target / "new.txt").exists()
        assert not (tmp_path / ".target.backup").exists()

    def test_staged_specs_swap_without_existing_target_creates_it(self, tmp_path):
        target = tmp_path / "target"
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "new.txt").write_text("new", encoding="utf-8")

        with staged_specs_swap(target=target, staging=staging) as live_root:
            assert (live_root / "new.txt").read_text(encoding="utf-8") == "new"

        assert target.is_dir()
        assert (target / "new.txt").exists()
        assert not (tmp_path / ".target.backup").exists()
        assert not staging.exists()

    def test_staged_specs_swap_removes_stale_backup_before_entering(self, tmp_path):
        target = tmp_path / "target"
        staging = tmp_path / "staging"
        stale_backup = tmp_path / ".target.backup"
        target.mkdir()
        staging.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        (staging / "new.txt").write_text("new", encoding="utf-8")
        stale_backup.mkdir()
        (stale_backup / "stale.txt").write_text("stale", encoding="utf-8")

        with staged_specs_swap(target=target, staging=staging) as live_root:
            assert (live_root / "new.txt").read_text(encoding="utf-8") == "new"

        assert target.is_dir()
        assert (target / "new.txt").exists()
        assert not stale_backup.exists()
        assert not staging.exists()

    def test_staged_specs_swap_first_swap_rollback_removes_swapped_in_directory(self, tmp_path):
        # First-ever mirror: no prior target exists, so the rollback path must
        # remove the swapped-in directory without restoring anything.
        target = tmp_path / "target"  # never created
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "new.txt").write_text("new", encoding="utf-8")

        with pytest.raises(RuntimeError), staged_specs_swap(target=target, staging=staging):
            raise RuntimeError("graph rebuild failed")

        assert not target.exists()
        assert not (tmp_path / ".target.backup").exists()
        assert not staging.exists()

    def test_staged_specs_swap_tolerates_backup_cleanup_failure(self, tmp_path, mocker):
        # The transaction has already succeeded when the backup is removed —
        # a failing cleanup must not surface as a swap failure. The no-op
        # rmtree simulates ignore_errors swallowing an undeletable backup.
        target = tmp_path / "target"
        staging = tmp_path / "staging"
        target.mkdir()
        staging.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        (staging / "new.txt").write_text("new", encoding="utf-8")
        mocker.patch("swax.fs.staged_specs_swap.shutil.rmtree")

        with staged_specs_swap(target=target, staging=staging) as live_root:
            assert (live_root / "new.txt").read_text(encoding="utf-8") == "new"

        assert (target / "new.txt").exists()
        # The stale backup stays behind for the next swap to remove.
        assert (tmp_path / ".target.backup").exists()
