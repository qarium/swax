"""Filesystem layout of a Swax project: the .swax/ directory and spec copying.

The facade re-exports the two routines that manage on-disk project layout:
ensure_swax_dir (idempotent .swax/ creation) and copy_specs (merging cloned
specs into the local path). All paths are pathlib.Path; imports inside the
cell are relative.
"""

from .copy_specs import copy_specs
from .ensure_swax_dir import ensure_swax_dir

__all__: list[str] = [
    "copy_specs",
    "ensure_swax_dir",
]
