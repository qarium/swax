"""Project configuration, environment variables, and SWAX_* validation.

The facade exposes contract entities incrementally. The three config models
are exposed here in task 2; the remaining entities (errors, env routines,
storage routines) are added in tasks 3-5 and the full surface is re-verified
in task 6.
"""

from .Config import Config
from .GitConfig import GitConfig
from .SpecsConfig import SpecsConfig

__all__: list[str] = ["Config", "GitConfig", "SpecsConfig"]
