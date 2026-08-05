"""Contract tests for the swax/applications facade.

The facade is an aggregator that re-exports the three use-case handlers (init,
discover, plan) under their consumer-facing aliases (run_init_handler,
run_discover_handler, run_plan_handler). These tests pin the facade surface so
the plan CLI handler can import run_plan_handler reliably.
"""

from swax.applications import (
    __all__,
    run_discover_handler,
    run_init_handler,
    run_plan_handler,
)
from swax.applications.plan import run_plan


def test_facade_exposes_all_three_handlers() -> None:
    """All three handlers are importable from the facade under their aliases."""
    assert run_init_handler is not None
    assert run_discover_handler is not None
    assert run_plan_handler is not None


def test_facade_handlers_are_callable() -> None:
    """Re-exported handlers are real callables, ready to invoke."""
    assert callable(run_init_handler)
    assert callable(run_discover_handler)
    assert callable(run_plan_handler)


def test_facade_all_lists_exactly_the_three_aliases() -> None:
    """`__all__` exposes the contract surface — the three aliases and nothing else."""
    assert __all__ == ["run_discover_handler", "run_init_handler", "run_plan_handler"]


def test_run_plan_alias_points_at_the_plan_subcell_use_case() -> None:
    """`run_plan_handler` aliases run_plan from the plan sub-cell."""
    assert run_plan_handler is run_plan
