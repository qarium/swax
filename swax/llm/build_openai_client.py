"""Factory: construct an OpenAI SDK client from SWAX_LLM_* env vars.

require_vars() runs first so the CLI fails fast on missing credentials before
any SDK object is created. The token and base URL are read straight from the
environment and handed to the SDK constructor; this routine never stores
SWAX_LLM_TOKEN. Base URL is assumed already validated (no /v1 segment) — the
SDK appends the version path itself.
"""

import os

from openai import OpenAI

from ..config import require_vars


def build_openai_client() -> OpenAI:
    """Build an OpenAI SDK client from SWAX_LLM_* environment variables.

    Returns:
        A ready-to-use OpenAI instance for OpenAIAdapter.

    Raises:
        MissingEnvironmentVariablesError: when SWAX_LLM_* validation fails.
    """
    require_vars()
    token = os.environ["SWAX_LLM_TOKEN"]
    base_url = os.environ["SWAX_LLM_BASE_URL"]
    return OpenAI(api_key=token, base_url=base_url)


__all__: list[str] = ["build_openai_client"]
