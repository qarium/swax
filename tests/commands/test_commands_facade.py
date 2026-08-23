"""Contract tests for the `swax/commands` facade.

The facade is an aggregator that re-exports the Click command handlers
(`init`, `discover`, `plan`, `update`) under their consumer-facing aliases
(`init_handler`, `discover_handler`, `plan_handler`, `update_handler`). These
tests pin the facade's surface so the cli entry point can rely on it.
"""

import click
from swax.commands import (
    __all__,
    discover_handler,
    init_handler,
    plan_handler,
    update_handler,
)
from swax.commands.discover import discover
from swax.commands.init import init
from swax.commands.plan import plan
from swax.commands.update import update


def test_facade_exposes_all_four_handlers() -> None:
    """All handlers are importable from the facade under their aliases."""
    assert init_handler is not None
    assert discover_handler is not None
    assert plan_handler is not None
    assert update_handler is not None


def test_facade_handlers_are_click_commands() -> None:
    """Re-exported handlers are real Click commands, ready for registration."""
    assert isinstance(init_handler, click.Command)
    assert isinstance(discover_handler, click.Command)
    assert isinstance(plan_handler, click.Command)
    assert isinstance(update_handler, click.Command)


def test_facade_all_lists_exactly_the_four_aliases() -> None:
    """`__all__` exposes the contract surface — the four aliases and nothing else."""
    assert __all__ == ["discover_handler", "init_handler", "plan_handler", "update_handler"]


def test_init_alias_points_at_the_init_subcell_command() -> None:
    """`init_handler` aliases the command from the init sub-cell."""
    assert init_handler is init


def test_discover_alias_points_at_the_discover_subcell_command() -> None:
    """`discover_handler` aliases the command from the discover sub-cell."""
    assert discover_handler is discover


def test_plan_alias_points_at_the_plan_subcell_command() -> None:
    """`plan_handler` aliases the command from the plan sub-cell."""
    assert plan_handler is plan


def test_update_alias_points_at_the_update_subcell_command() -> None:
    """`update_handler` aliases the command from the update sub-cell."""
    assert update_handler is update
