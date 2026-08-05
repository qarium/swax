"""Commands cell for `swax plan`.

The facade re-exports the Click command `plan`, the thin handler that delegates
to the run_plan use-case, echoes the Markdown Impact Report, and maps the nine
documented domain exceptions to click.ClickException. This cell contains no
orchestration — it only maps the documented domain exceptions to
click.ClickException.
"""

from .plan import plan

__all__: list[str] = ["plan"]
