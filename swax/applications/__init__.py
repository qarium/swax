"""Application use-cases and their aggregator facade.

The facade is built incrementally: task 16 adds the init use-case cell, task 17
adds the discover use-case cell, task 18 wires this package to re-export
run_init_handler and run_discover_handler, and the plan use-case adds the
run_plan_handler re-export. Consumers import the use-cases from here, not from
the sub-cells.
"""

from .discover import run_discover as run_discover_handler
from .init import run_init as run_init_handler
from .plan import run_plan as run_plan_handler

__all__: list[str] = ["run_discover_handler", "run_init_handler", "run_plan_handler"]
