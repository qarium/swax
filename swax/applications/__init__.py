"""Application use-cases and their aggregator facade.

The facade is built incrementally: task 16 adds the init use-case cell, task 17
adds the discover use-case cell, and task 18 wires this package to re-export
both handlers (run_init_handler, run_discover_handler). Consumers import the
use-cases from here, not from the sub-cells.
"""

from .discover import run_discover as run_discover_handler
from .init import run_init as run_init_handler

__all__: list[str] = ["run_discover_handler", "run_init_handler"]
