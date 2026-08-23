"""Spec mirroring routine: byte-level classification of two specs trees.

compare_specs is the read-only predicate at the head of the update
transaction: it decides which branch run_update takes before anything on
disk is mutated.
"""

import filecmp
import pathlib

from .specs_changes import SpecsChanges


def compare_specs(local_root: pathlib.Path, remote_root: pathlib.Path) -> SpecsChanges:
    """Classify file-level differences between the local specs tree and the remote clone.

    Args:
        local_root: local specs directory (may not exist).
        remote_root: specs directory inside the fresh clone.

    Returns:
        changes: files only in `remote_root` are added, files only in
            `local_root` are removed, files in both with differing bytes are
            updated; every list is sorted and keyed by POSIX-relative path.
    """

    local_files = (
        {p.relative_to(local_root).as_posix(): p for p in local_root.rglob("*") if p.is_file()}
        if local_root.exists()
        else {}
    )

    remote_files = {
        p.relative_to(remote_root).as_posix(): p for p in remote_root.rglob("*") if p.is_file()
    }

    added = sorted(set(remote_files) - set(local_files))
    removed = sorted(set(local_files) - set(remote_files))
    updated = sorted(
        rel
        for rel in set(local_files) & set(remote_files)
        if not filecmp.cmp(local_files[rel], remote_files[rel], shallow=False)
    )

    return SpecsChanges(added=added, updated=updated, removed=removed)


__all__: list[str] = [
    "compare_specs",
]
