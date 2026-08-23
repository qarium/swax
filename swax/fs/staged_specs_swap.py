"""Spec mirroring routine: transactional replacement of the live specs directory.

staged_specs_swap moves the live specs directory aside to a backup, renames
the fully assembled staging directory into place, and removes the backup on
normal exit (best effort — a leftover is removed on the next swap and a
removal failure never fails an otherwise completed transaction). On exception
the swapped-in directory is removed and the backup is restored — the single
rollback point of the update transaction. Renames stay inside the target's
parent directory (same filesystem, atomic).
"""

import contextlib
import logging
import pathlib
import shutil
from collections.abc import Iterator

logger = logging.getLogger(__name__)


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
        # Best effort: the transaction has already succeeded at this point,
        # so a cleanup failure must not surface as a rebuild failure. A
        # leftover backup is removed the next time the swap is entered.
        shutil.rmtree(backup, ignore_errors=True)

        if backup.exists():
            logger.warning(
                "backup removal after swap failed; stale backup left for the next run",
                extra={"backup": backup.name},
            )


__all__: list[str] = [
    "staged_specs_swap",
]
