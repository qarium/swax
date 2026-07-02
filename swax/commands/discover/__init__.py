"""Commands cell for `swax discover`.

The facade re-exports the Click command `discover`, the thin handler that
delegates to the run_discover use-case. This cell contains no orchestration —
it only maps the six documented domain exceptions to click.ClickException.
"""

from .discover import discover

__all__: list[str] = ["discover"]
