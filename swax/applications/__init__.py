"""Application use-cases and their aggregator facade.

The facade re-exports the four use-case handlers (init, discover, plan,
update) under their consumer-facing aliases plus the update domain error
GraphRebuildFailedError. Consumers import the use-cases from here, not from
the sub-cells.
"""

from .discover import run_discover as run_discover_handler
from .init import run_init as run_init_handler
from .plan import run_plan as run_plan_handler
from .update import GraphRebuildFailedError
from .update import run_update as run_update_handler

__all__: list[str] = [
    "GraphRebuildFailedError",
    "run_discover_handler",
    "run_init_handler",
    "run_plan_handler",
    "run_update_handler",
]
