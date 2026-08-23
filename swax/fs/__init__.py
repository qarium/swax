"""Filesystem layout of a Swax project: the .swax/ directory, spec copying, and spec mirroring.

The facade re-exports the entities that manage the on-disk project layout:
ensure_swax_dir (idempotent .swax/ creation), copy_specs (merging cloned specs
into the local path), the change classification value object SpecsChanges, and
the mirroring path-guard error UnsafeSpecsLocationError. All paths are
pathlib.Path; imports inside the cell are relative.
"""

from .copy_specs import copy_specs
from .ensure_swax_dir import ensure_swax_dir
from .errors import UnsafeSpecsLocationError
from .specs_changes import SpecsChanges

__all__: list[str] = [
    "SpecsChanges",
    "UnsafeSpecsLocationError",
    "copy_specs",
    "ensure_swax_dir",
]
