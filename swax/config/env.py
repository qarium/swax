"""Environment routines: dotenv loading and SWAX_* credential validation.

These routines form the credential boundary of the CLI. load_env is invoked
early by the Click group callback; require_vars is invoked lazily by the
use-cases that need LLM credentials (run_discover). SWAX_LLM_TOKEN is never
written to logs — these routines only read it and pass it forward.
"""

import os
import pathlib

from dotenv import load_dotenv

from .errors import (
    InvalidLLMBaseURLError,
    InvalidLLMProtocolError,
    MissingEnvironmentVariablesError,
)

REQUIRED_VARS: tuple[str, ...] = (
    "SWAX_LLM_MODEL",
    "SWAX_LLM_PROTOCOL",
    "SWAX_LLM_BASE_URL",
    "SWAX_LLM_TOKEN",
)
ALLOWED_PROTOCOLS: tuple[str, ...] = ("anthropic", "openai")


def load_env(env_file: pathlib.Path) -> None:
    """Load a dotenv file without overriding variables already in the shell.

    Args:
        env_file: path to the dotenv file from the --env-file option.

    A missing file is not an error — the routine returns silently so the CLI
    can run without a committed .env file. Real environment variables keep
    precedence over file values (override=False).
    """
    if not env_file.exists():
        return
    load_dotenv(env_file, override=False)


def require_vars() -> dict[str, str]:
    """Validate that all mandatory SWAX_* variables are present and non-empty.

    Empty and whitespace-only values count as missing.

    Returns:
        A name-to-value mapping of the mandatory variables for caller
        convenience.

    Raises:
        MissingEnvironmentVariablesError: when any mandatory variable is
            missing or whitespace-only.
    """
    missing: list[str] = []

    for name in REQUIRED_VARS:
        value = os.environ.get(name)
        if not value or not value.strip():
            missing.append(name)

    if missing:
        raise MissingEnvironmentVariablesError(missing=missing)

    return {name: os.environ[name] for name in REQUIRED_VARS}


def parse_protocol(value: str) -> str:
    """Validate SWAX_LLM_PROTOCOL as a supported provider identifier.

    Args:
        value: raw value from the environment.

    Returns:
        The validated protocol value when it is one of the supported providers.

    Raises:
        InvalidLLMProtocolError: when the value is outside
            ("anthropic", "openai").
    """
    if value not in ALLOWED_PROTOCOLS:
        raise InvalidLLMProtocolError(value=value, allowed=ALLOWED_PROTOCOLS)
    return value


def parse_base_url(value: str) -> str:
    """Reject SWAX_LLM_BASE_URL that includes a version segment (/v1, /v2).

    Args:
        value: raw value from the environment.

    Returns:
        The base URL with any trailing slash removed.

    Raises:
        InvalidLLMBaseURLError: when the URL ends with /v1 or /v2. A trailing
            slash is stripped before the version check.
    """
    stripped = value.rstrip("/")
    if stripped.endswith(("/v1", "/v2")):
        raise InvalidLLMBaseURLError(value=value)
    return stripped


__all__: list[str] = [
    "load_env",
    "parse_base_url",
    "parse_protocol",
    "require_vars",
]
