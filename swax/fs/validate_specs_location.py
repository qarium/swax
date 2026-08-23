"""Spec mirroring routine: path guard for the mirroring target.

validate_specs_location refuses mirroring targets that would cover the
project itself — mirroring into the project root would delete the project
together with its .swax/ directory. It runs before any mutation.
"""

import pathlib

from .errors import UnsafeSpecsLocationError


def validate_specs_location(project_root: pathlib.Path, specs_location: pathlib.Path) -> None:
    """Guard the mirroring target: refuse locations covering the project itself.

    Args:
        project_root: root of the Swax project (where .swax/ lives).
        specs_location: configured local specs path.

    Raises:
        UnsafeSpecsLocationError: when `specs_location` equals the project
            root or is one of its ancestors — mirroring would cover the
            project itself.
    """

    project = project_root.resolve()
    specs = specs_location.resolve()

    if specs == project or project.is_relative_to(specs):
        raise UnsafeSpecsLocationError(path=specs_location)


__all__: list[str] = [
    "validate_specs_location",
]
