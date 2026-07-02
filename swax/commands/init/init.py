"""Click handler for the `swax init` command.

Thin CLI handler: it collects the repository URL, specs location, and local
download path through interactive prompts, then delegates to the run_init
use-case. The two domain exceptions run_init can raise (RepositoryCloneError,
SpecsNotFoundError) are mapped to click.ClickException so every failure surfaces
a uniform, user-facing message and exits with code 1. No orchestration lives
here — only prompts and exception mapping.

SwaxContext is imported only as a type hint. The main group stores a
SwaxContext on the Click context object (ctx.obj); @click.pass_obj forwards it
as this handler's first argument. The import is deferred to TYPE_CHECKING to
keep the cli <-> commands edge acyclic — cli.__main__ lazily registers the
commands, and the commands only type-hint (never import at runtime) the cli
cell.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import click
from swax.applications import run_init_handler as run_init
from swax.git import RepositoryCloneError, SpecsNotFoundError

if TYPE_CHECKING:
    from swax.cli import SwaxContext


@click.command()
@click.pass_obj
def init(_ctx: SwaxContext) -> None:
    """Initialize a Swax project: prompt for inputs, then run the init use-case.

    Prompts are the sole source of user input. The current working directory is
    used as the project root.
    """
    repo_url = click.prompt("Repository URL")
    specs_location = click.prompt("Path to specs inside the repo")
    download_path = pathlib.Path(click.prompt("Local download path"))
    project_root = pathlib.Path.cwd()
    try:
        run_init(repo_url, specs_location, download_path, project_root)
    except RepositoryCloneError as exc:
        raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}") from exc
    except SpecsNotFoundError as exc:
        raise click.ClickException(f"Specs not found at {exc.path}") from exc


__all__: list[str] = ["init"]
