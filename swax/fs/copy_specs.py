"""Filesystem layout routine: merge downloaded specs into the local project path.

copy_specs is the boundary between the temporary clone produced by clone_specs
and the persistent local path declared in SpecsConfig.location. It merges the
clone into the local path so re-runs pick up spec updates.
"""

import pathlib
import shutil


def copy_specs(source: pathlib.Path, destination: pathlib.Path) -> None:
    """Recursively merge cloned specs into the local destination path.

    Args:
        source: directory of specs inside the clone (output of clone_specs).
        destination: local path declared in SpecsConfig.location.

    Parent directories of the destination are created as needed, and existing
    files are overwritten on re-runs. Symlinks in the clone are copied as
    regular files: shutil.copytree uses its default symlinks=False, so the
    target content is materialized rather than the link itself.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source, destination, dirs_exist_ok=True)


__all__: list[str] = [
    "copy_specs",
]
