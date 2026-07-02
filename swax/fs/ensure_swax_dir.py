"""Filesystem layout routine: guarantee the .swax/ directory exists.

ensure_swax_dir is the idempotent entry point every write path calls before
persisting config.yml or traceability.yml under a project root.
"""

import pathlib


def ensure_swax_dir(project_root: pathlib.Path) -> pathlib.Path:
    """Guarantee the .swax/ directory exists under the project root.

    Args:
        project_root: root of the Swax project (where .swax/ lives).

    Returns:
        The resolved .swax/ directory, ready for config.yml and
        traceability.yml writes.
    """
    swax_dir = project_root / ".swax"
    swax_dir.mkdir(parents=True, exist_ok=True)

    return swax_dir


__all__: list[str] = [
    "ensure_swax_dir",
]
