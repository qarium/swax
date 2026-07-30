"""Click handler for the `swax discover` command.

Thin CLI handler: it resolves the project root from the current working
directory and delegates to the run_discover use-case. All orchestration lives in
run_discover; this handler only maps the six documented domain exceptions to
click.ClickException so every failure surfaces a uniform, user-facing message and
exits with code 1. No interactive prompts — discover reads everything from
.swax/config.yml and the environment. Generic Exception is never caught, only the
documented domain errors, and SWAX_LLM_TOKEN never appears in any message.

SwaxContext is imported only as a type hint. The main group stores a SwaxContext
on the Click context object (ctx.obj); @click.pass_obj forwards it as this
handler's first argument. The import is deferred to TYPE_CHECKING to keep the
cli <-> commands edge acyclic — cli.__main__ lazily registers the commands, and
the commands only type-hint (never import at runtime) the cli cell. The obj is
intentionally unused by this handler; it is accepted for API parity with the
init handler.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import click

from ...applications import run_discover_handler as run_discover
from ...config import MissingEnvironmentVariablesError
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
def discover(_ctx: SwaxContext) -> None:
    """Rebuild the traceability graph: run the discover use-case.

    The project root is the current working directory. No prompts are issued;
    discover reads its inputs from ``.swax/config.yml`` and the environment.
    """
    project_root = pathlib.Path.cwd()

    try:
        run_discover(project_root)
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


__all__: list[str] = ["discover"]
