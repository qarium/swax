"""Contract tests for the `swax/commands` facade.

The facade is an aggregator that re-exports the two Click command handlers
(`init`, `discover`) under their consumer-facing aliases
(`init_handler`, `discover_handler`). These tests pin the facade's surface so a
later task (cli registration) can rely on it.
"""

import click
from swax.commands import __all__, discover_handler, init_handler
from swax.commands.discover import discover
from swax.commands.init import init


def test_facade_exposes_both_handlers() -> None:
    """Both handlers are importable from the facade under their aliases."""
    assert init_handler is not None
    assert discover_handler is not None


def test_facade_handlers_are_click_commands() -> None:
    """Re-exported handlers are real Click commands, ready for registration."""
    assert isinstance(init_handler, click.Command)
    assert isinstance(discover_handler, click.Command)


def test_facade_all_lists_exactly_the_two_aliases() -> None:
    """`__all__` exposes the contract surface — both aliases and nothing else."""
    assert __all__ == ["discover_handler", "init_handler"]


def test_init_alias_points_at_the_init_subcell_command() -> None:
    """`init_handler` aliases the command from the init sub-cell."""
    assert init_handler is init


def test_discover_alias_points_at_the_discover_subcell_command() -> None:
    """`discover_handler` aliases the command from the discover sub-cell."""
    assert discover_handler is discover
