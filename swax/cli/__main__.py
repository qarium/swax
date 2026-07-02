"""Lazy registration of subcommands and the ``swax`` console-script entry point.

Importing this module registers ``init`` and ``discover`` on the ``main`` group
and exposes ``main`` as the console-script target
(``swax = "swax.cli.__main__:main"``). Registration lives here, not in
``__init__``, to break the cli <-> commands cycle: the commands cell imports the
cli cell for type hints, so the cli cell must not import the commands cell at
package import time.
"""

from swax.cli.main import main
from swax.commands import discover_handler, init_handler

main.add_command(discover_handler, name="discover")
main.add_command(init_handler, name="init")

if __name__ == "__main__":
    main()
