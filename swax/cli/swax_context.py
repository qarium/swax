"""SwaxContext pydantic pass object.

Carries CLI parameters from the top-level Click group to its subcommands. The
``main`` group constructs a SwaxContext from the ``--env-file`` option and stores
it as ``ctx.obj``; subcommands receive it via ``@click.pass_obj``. ``env_file`` is
the resolved dotenv path; ``config`` is an optional cache that starts as ``None``
— ``init`` writes configuration rather than reading it, and ``discover`` reads it
lazily, so the cache is populated on demand by whichever subcommand needs it.
"""

from __future__ import annotations

import pathlib
from typing import Optional

from pydantic import BaseModel, ConfigDict
from swax.config import Config


class SwaxContext(BaseModel):
    """Click pass object shared between the ``main`` group and its subcommands.

    Args:
        env_file: path to the dotenv file from the ``--env-file`` option.
        config: optional cached project configuration; ``None`` until a
            subcommand populates it.
    """

    model_config = ConfigDict(kw_only=True)

    env_file: pathlib.Path
    config: Optional[Config] = None


__all__: list[str] = ["SwaxContext"]
