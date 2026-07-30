"""Top-level Click group: the ``swax`` entry point.

The group parses the ``--env-file`` option, loads the environment (silently when
the file is missing — ``load_env`` handles that), and stores a ``SwaxContext`` on
the Click context object for subcommands. Subcommand registration is deferred to
``swax.cli.__main__`` to keep the cli <-> commands dependency acyclic: this
module (and the package ``__init__``) never imports the commands cell, and the
commands cell only type-hints (never imports at runtime) the cli cell.
"""

from __future__ import annotations

import pathlib

import click

from ..config import load_env
from .swax_context import SwaxContext


@click.group()
@click.option(
    "--env-file",
    type=click.Path(exists=False, dir_okay=False, path_type=pathlib.Path),
    default=".env",
    show_default=True,
    help="Path to the environment file.",
)
@click.pass_context
def main(ctx: click.Context, env_file: pathlib.Path) -> None:
    """Swax — API traceability graph builder."""
    load_env(env_file)
    ctx.obj = SwaxContext(env_file=env_file)


__all__: list[str] = ["main"]
