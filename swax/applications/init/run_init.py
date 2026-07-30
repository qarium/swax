"""Application use-case: initialize a Swax project.

run_init orchestrates project initialization across three domain cells
(config, git, fs). It assembles a Config, persists it under .swax/, then clones
the source repository and copies its specs into the local download path. The
configuration is written before the clone so a clone failure still leaves the
user with .swax/config.yml to inspect. RepositoryCloneError and
SpecsNotFoundError propagate uncaught — the CLI handler maps them to
click.ClickException.
"""

import logging
import pathlib

from ...config import Config, GitConfig, SpecsConfig, save_config
from ...fs import copy_specs, ensure_swax_dir
from ...git import clone_specs

logger = logging.getLogger(__name__)


def run_init(
    repo_url: str,
    specs_location: str,
    download_path: pathlib.Path,
    project_root: pathlib.Path,
) -> None:
    """Initialize a Swax project: persist config, clone source, copy specs.

    The config is written to .swax/config.yml before cloning so it survives a
    clone failure. The clone_specs context guarantees temporary-directory
    cleanup on every outcome.

    Args:
        repo_url: clone URL of the source repository.
        specs_location: subdirectory inside the repository holding the specs.
        download_path: local destination for the copied specs.
        project_root: root of the Swax project (.swax/ lives here).

    Raises:
        RepositoryCloneError: when cloning the repository fails (propagated).
        SpecsNotFoundError: when specs_location is absent in the clone
            (propagated).
    """
    config = Config(
        git=GitConfig(url=repo_url, location=specs_location),
        specs=SpecsConfig(type="openapi", location=str(download_path)),
    )

    swax_dir = ensure_swax_dir(project_root)
    save_config(config, swax_dir / "config.yml")

    logger.info("init started", extra={"project_root": str(project_root)})

    with clone_specs(repo_url, specs_location) as specs_path:
        copy_specs(source=specs_path, destination=download_path)

    logger.info("init completed", extra={"project_root": str(project_root)})


__all__: list[str] = ["run_init"]
