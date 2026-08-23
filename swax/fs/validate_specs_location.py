"""Spec mirroring routine: path guard for the mirroring target.

validate_specs_location refuses mirroring targets that would cover the
project itself or its .swax/ directory — mirroring into the project root
would delete the project together with .swax/, and mirroring into .swax/
would delete the saved configuration and the traceability graph. It runs
before any mutation.
"""

import pathlib

from .errors import UnsafeSpecsLocationError


def validate_specs_location(project_root: pathlib.Path, specs_location: pathlib.Path) -> None:
    """Guard the mirroring target: refuse locations covering the project or .swax.

    Args:
        project_root: root of the Swax project (where .swax/ lives).
        specs_location: configured local specs path.

    Raises:
        UnsafeSpecsLocationError: when `specs_location` equals the project
            root, is one of its ancestors, or otherwise covers the .swax/
            directory — mirroring would destroy the project or its saved
            state.
    """

    project = project_root.resolve()
    specs = specs_location.resolve()
    swax_dir = (project_root / ".swax").resolve()

    covers_project = specs == project or project.is_relative_to(specs)
    covers_swax_dir = specs == swax_dir or swax_dir.is_relative_to(specs)

    if covers_project or covers_swax_dir:
        raise UnsafeSpecsLocationError(path=specs_location)


__all__: list[str] = [
    "validate_specs_location",
]
