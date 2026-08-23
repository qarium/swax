"""Contract tests for the swax/applications facade.

The facade is an aggregator that re-exports the four use-case handlers (init,
discover, plan, update) under their consumer-facing aliases (run_init_handler,
run_discover_handler, run_plan_handler, run_update_handler) plus the update
domain error GraphRebuildFailedError. These tests pin the facade surface so
the plan and update CLI handlers can import their use-cases reliably.
"""

from swax.applications import (
    GraphRebuildFailedError,
    __all__,
    run_discover_handler,
    run_init_handler,
    run_plan_handler,
    run_update_handler,
)
from swax.applications.plan import run_plan
from swax.applications.update import run_update


def test_facade_exposes_all_four_handlers() -> None:
    """All four handlers are importable from the facade under their aliases."""
    assert run_init_handler is not None
    assert run_discover_handler is not None
    assert run_plan_handler is not None
    assert run_update_handler is not None


def test_facade_handlers_are_callable() -> None:
    """Re-exported handlers are real callables, ready to invoke."""
    assert callable(run_init_handler)
    assert callable(run_discover_handler)
    assert callable(run_plan_handler)
    assert callable(run_update_handler)


def test_facade_all_lists_exactly_the_five_names() -> None:
    """`__all__` exposes the contract surface — four aliases plus the domain error."""
    assert __all__ == [
        "GraphRebuildFailedError",
        "run_discover_handler",
        "run_init_handler",
        "run_plan_handler",
        "run_update_handler",
    ]


def test_run_plan_alias_points_at_the_plan_subcell_use_case() -> None:
    """`run_plan_handler` aliases run_plan from the plan sub-cell."""
    assert run_plan_handler is run_plan


def test_run_update_alias_points_at_the_update_subcell_use_case() -> None:
    """`run_update_handler` aliases run_update from the update sub-cell."""
    assert run_update_handler is run_update


def test_graph_rebuild_failed_error_is_a_domain_error() -> None:
    """GraphRebuildFailedError re-exported from the facade is an Exception subclass."""
    assert issubclass(GraphRebuildFailedError, Exception)
