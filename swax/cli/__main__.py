"""Lazy registration of subcommands and the ``swax`` console-script entry point.

Importing this module registers ``init``, ``discover``, ``plan``, and ``update`` on the
``main`` group and exposes ``main`` as the console-script target
(``swax = "swax.cli.__main__:main"``). Registration lives here, not in
``__init__``, to break the cli <-> commands cycle: the commands cell imports the
cli cell for type hints, so the cli cell must not import the commands cell at
package import time.
"""

from ..commands import discover_handler, init_handler, plan_handler, update_handler
from .main import main

main.add_command(discover_handler, name="discover")
main.add_command(init_handler, name="init")
main.add_command(plan_handler, name="plan")
main.add_command(update_handler, name="update")

if __name__ == "__main__":
    main()
