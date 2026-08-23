"""Click handler for the `swax update` command.

Thin CLI handler: it resolves the project root from the current working
directory and delegates to the run_update use-case, then echoes the returned
update summary to stdout. All orchestration — spec mirroring, the conditional
graph rebuild, the transaction rollback — lives in run_update; this handler only
maps the ten documented domain exceptions to click.ClickException so every
failure surfaces a uniform, user-facing message and exits with code 1.
No interactive prompts — update reads everything from .swax/config.yml and the
environment. Generic Exception is never caught, only the documented domain
errors, and SWAX_LLM_TOKEN never appears in any message.

SwaxContext is imported only as a type hint. The main group stores a SwaxContext
on the Click context object (ctx.obj); @click.pass_obj forwards it as this
handler's first argument. The import is deferred to TYPE_CHECKING to keep the
cli <-> commands edge acyclic — cli.__main__ lazily registers the commands, and
the commands only type-hint (never import at runtime) the cli cell. The obj is
intentionally unused by this handler; it is accepted for API parity with the
init, discover, and plan handlers.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import click

from ...applications import GraphRebuildFailedError
from ...applications import run_update_handler as run_update
from ...config import MissingEnvironmentVariablesError
from ...fs import UnsafeSpecsLocationError
from ...git import RepositoryCloneError, SpecsNotFoundError
from ...llm import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from ...openapi import SpecParseError

if TYPE_CHECKING:
    from ...cli import SwaxContext


@click.command()
@click.pass_obj
def update(_ctx: SwaxContext) -> None:  # noqa: C901 — one except row per documented domain error
    """Update local specs to the remote state and rebuild the traceability graph.

    The project root is the current working directory. No prompts are issued;
    update reads its inputs from ``.swax/config.yml`` and the environment.

    Args:
        _ctx: Click context whose obj is a SwaxContext — unused, accepted for
            handler parity with the init, discover, and plan handlers.

    Raises:
        click.ClickException: on any documented domain failure of run_update,
            with a user-facing message (exit code 1).
    """
    project_root = pathlib.Path.cwd()

    try:
        output = run_update(project_root)
    except UnsafeSpecsLocationError as exc:
        raise click.ClickException(f"Refusing to mirror into {exc.path}") from exc
    except GraphRebuildFailedError as exc:
        raise click.ClickException(f"Graph rebuild failed: {exc.reason}; specs restored.") from exc
    except RepositoryCloneError as exc:
        raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}") from exc
    except SpecsNotFoundError as exc:
        raise click.ClickException(f"Specs not found at {exc.path}") from exc
    except MissingEnvironmentVariablesError as exc:
        raise click.ClickException(f"Missing env vars: {', '.join(exc.missing)}") from exc
    except SpecParseError as exc:
        raise click.ClickException(f"Failed to parse {exc.path}: {exc.reason}") from exc
    except LLMRateLimitedError as exc:
        raise click.ClickException("LLM rate limited; retry later") from exc
    except LLMCallError as exc:
        raise click.ClickException(f"LLM call failed: {exc.reason}") from exc
    except UnsupportedLLMProtocolError as exc:
        raise click.ClickException(f"Unsupported LLM protocol: {exc.protocol}") from exc
    except LLMResponseParseError as exc:
        raise click.ClickException(f"LLM response parse failed: {exc.reason}") from exc

    click.echo(output)


__all__: list[str] = ["update"]
