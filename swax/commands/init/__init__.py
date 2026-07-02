"""Commands cell for `swax init`.

The facade re-exports the Click command `init`, the thin handler that prompts the
user and delegates to the run_init use-case. This cell contains no
orchestration — it only maps domain exceptions to click.ClickException.
"""

from .init import init

__all__: list[str] = ["init"]
