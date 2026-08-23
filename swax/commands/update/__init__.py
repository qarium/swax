"""Commands cell for `swax update`.

The facade re-exports the Click command `update`, the thin handler that delegates
to the run_update use-case, echoes the update summary, and maps the ten
documented domain exceptions to click.ClickException. This cell contains no
orchestration — mirroring, the conditional graph rebuild, and the transaction
rollback all live in the applications/update cell.
"""

from .update import update

__all__: list[str] = ["update"]
