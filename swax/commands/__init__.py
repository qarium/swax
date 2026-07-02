"""Command-layer facade re-exporting the CLI handlers.

The facade is built incrementally: task 19 adds the init command cell, task 20
adds the discover command cell, and task 21 wires this package to re-export both
handlers (init_handler, discover_handler) so the cli entry point can register
them through a single import. Consumers import the commands from here, not from
the sub-cells.
"""

from .discover import discover as discover_handler
from .init import init as init_handler

__all__: list[str] = ["discover_handler", "init_handler"]
