"""Tests for staged_specs_swap — transactional replacement of the specs dir.

Covers the replace-and-remove-backup swap, rollback on exception, the
first-swap case without a prior target, stale-backup cleanup, and the
best-effort semantics of the backup removal. All filesystem operations use
tmp_path.
"""

import pytest
from swax.fs import staged_specs_swap


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
