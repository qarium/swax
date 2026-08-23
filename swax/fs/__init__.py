"""Filesystem layout of a Swax project: the .swax/ directory, spec copying, and spec mirroring.

The facade re-exports the entities that manage the on-disk project layout:
ensure_swax_dir (idempotent .swax/ creation), copy_specs (merging cloned specs
into the local path), compare_specs (byte-level change classification of two
specs trees), the change classification value object SpecsChanges, the
mirroring path guard validate_specs_location with its domain error
UnsafeSpecsLocationError, and staged_specs_swap (transactional replacement of
the live specs directory — the single rollback point of spec mirroring). All
paths are pathlib.Path; imports inside the cell are relative.
"""

from .compare_specs import compare_specs
from .copy_specs import copy_specs
from .ensure_swax_dir import ensure_swax_dir
from .errors import UnsafeSpecsLocationError
from .specs_changes import SpecsChanges
from .staged_specs_swap import staged_specs_swap
from .validate_specs_location import validate_specs_location

__all__: list[str] = [
    "SpecsChanges",
    "UnsafeSpecsLocationError",
    "compare_specs",
    "copy_specs",
    "ensure_swax_dir",
    "staged_specs_swap",
    "validate_specs_location",
]
