"""Read-only access to the git repository holding API specifications.

The facade re-exports clone_specs (a context manager that shallow-clones the
specs repository into a temporary directory and yields the specs subdirectory)
and the two domain errors it raises. Swax never commits or pushes — it clones,
reads, and discards the clone.
"""

from .clone_specs import clone_specs
from .errors import RepositoryCloneError, SpecsNotFoundError

__all__: list[str] = [
    "RepositoryCloneError",
    "SpecsNotFoundError",
    "clone_specs",
]
