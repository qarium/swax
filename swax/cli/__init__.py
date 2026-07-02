"""CLI entry point: the top-level Click group and the SwaxContext pass object.

The facade exposes ``main`` and ``SwaxContext``. Subcommands (``init``,
``discover``) are registered lazily in ``swax.cli.__main__`` — never here — so
importing ``swax.cli`` does not pull in the commands cell, keeping the cli <->
commands edge acyclic.
"""

from .main import main
from .SwaxContext import SwaxContext

__all__: list[str] = ["SwaxContext", "main"]
