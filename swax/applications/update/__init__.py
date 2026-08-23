"""Application use-case cell for updating local specs to the remote state.

The facade exposes run_update, the transactional use-case that mirrors the
local specs directory to the remote state by the saved configuration and
conditionally rebuilds the traceability graph, plus its domain error
GraphRebuildFailedError. Cell-internal helpers stay off the facade.
"""

from .errors import GraphRebuildFailedError
from .run_update import run_update

__all__: list[str] = ["GraphRebuildFailedError", "run_update"]
