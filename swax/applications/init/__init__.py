"""Application use-case cell for project initialization.

The facade re-exports run_init, the use-case that orchestrates config
persistence, repository cloning, and spec copying across the config, git, and
fs cells. This cell contains no business logic — it only sequences calls.
"""

from .run_init import run_init

__all__: list[str] = ["run_init"]
