"""Project configuration, environment variables, and SWAX_* validation.

The facade exposes contract entities incrementally. The three config models
are exposed here in task 2; the remaining entities (errors, env routines,
storage routines) are added in tasks 3-5 and the full surface is re-verified
in task 6.
"""

from .config import Config
from .env import (
    load_env,
    parse_base_url,
    parse_protocol,
    require_vars,
)
from .errors import (
    InvalidLLMBaseURLError,
    InvalidLLMProtocolError,
    MissingEnvironmentVariablesError,
)
from .git_config import GitConfig
from .specs_config import SpecsConfig
from .storage import load_config, save_config

__all__: list[str] = [
    "Config",
    "GitConfig",
    "InvalidLLMBaseURLError",
    "InvalidLLMProtocolError",
    "MissingEnvironmentVariablesError",
    "SpecsConfig",
    "load_config",
    "load_env",
    "parse_base_url",
    "parse_protocol",
    "require_vars",
    "save_config",
]
