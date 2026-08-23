"""Spec mirroring routine: path guard for the mirroring target.

validate_specs_location refuses mirroring targets outside the project and
targets that would cover the project itself or its .swax/ directory —
mirroring into the project root would delete the project together with
.swax/, mirroring into .swax/ would delete the saved configuration and the
traceability graph, and mirroring anywhere else outside the project would
delete a directory swax does not own (an absolute configured location
overrides the project root entirely, so a free-form location must not be
able to escape it). It runs before any mutation.
"""

import pathlib

from .errors import UnsafeSpecsLocationError


def validate_specs_location(project_root: pathlib.Path, specs_location: pathlib.Path) -> None:
    """Guard the mirroring target: refuse locations outside the project or covering .swax.

    Args:
        project_root: root of the Swax project (where .swax/ lives).
        specs_location: configured local specs path.

    Raises:
        UnsafeSpecsLocationError: when `specs_location` is not a strict
            descendant of the project root (an outside directory, the root
            itself, or one of its ancestors) or otherwise covers the .swax/
            directory — mirroring would destroy a directory swax does not
            own, the project, or its saved state.
    """

    project = project_root.resolve()
    specs = specs_location.resolve()
    swax_dir = (project_root / ".swax").resolve()

    inside_project = specs != project and specs.is_relative_to(project)
    covers_swax_dir = specs == swax_dir or swax_dir.is_relative_to(specs)

    if not inside_project or covers_swax_dir:
        raise UnsafeSpecsLocationError(path=specs_location)


__all__: list[str] = [
    "validate_specs_location",
]
