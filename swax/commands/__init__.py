"""Command-layer facade re-exporting the CLI handlers.

The facade is built incrementally: task 19 adds the init command cell, task 20
adds the discover command cell, task 21 wires this package to re-export the init
and discover handlers (init_handler, discover_handler), the plan command adds
the plan_handler re-export, and the update command adds the update_handler
re-export so the cli entry point can register all four handlers through a
single import. Consumers import the commands from here, not from the
sub-cells.
"""

from .discover import discover as discover_handler
from .init import init as init_handler
from .plan import plan as plan_handler
from .update import update as update_handler

__all__: list[str] = [
    "discover_handler",
    "init_handler",
    "plan_handler",
    "update_handler",
]
