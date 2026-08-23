"""Spec mirroring routine: transactional replacement of the live specs directory.

staged_specs_swap moves the live specs directory aside to a backup, renames
the fully assembled staging directory into place, and removes the backup on
normal exit. On exception the swapped-in directory is removed and the backup
is restored — the single rollback point of the update transaction. Renames
stay inside the target's parent directory (same filesystem, atomic).
"""

import contextlib
import pathlib
import shutil
from collections.abc import Iterator


@contextlib.contextmanager
def staged_specs_swap(target: pathlib.Path, staging: pathlib.Path) -> Iterator[pathlib.Path]:
    """Replace the live specs directory with the prepared staging directory.

    Args:
        target: the live local specs directory to replace.
        staging: the fully assembled new state, located next to `target`.

    Yields:
        The target path, valid as the live directory inside the with block.

    Raises:
        BaseException: re-raised unchanged after cleanup when the with block
            fails — the swapped-in directory is removed and the backup is
            restored to `target`.
    """

    backup = target.with_name(f".{target.name}.backup")

    if backup.exists():
        shutil.rmtree(backup)

    had_target = target.exists()

    if had_target:
        target.rename(backup)

    try:
        staging.rename(target)

        yield target

    except BaseException:
        shutil.rmtree(target, ignore_errors=True)

        if had_target:
            backup.rename(target)

        raise

    if had_target:
        shutil.rmtree(backup)


__all__: list[str] = [
    "staged_specs_swap",
]
