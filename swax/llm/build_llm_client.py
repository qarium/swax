"""Factory: select the LLM adapter based on SWAX_LLM_PROTOCOL.

Reads SWAX_LLM_PROTOCOL and SWAX_LLM_MODEL from the environment and returns the
matching adapter wrapping its SDK client. Switching providers therefore needs
no consumer code change; selecting a model needs no code change either. An
unknown protocol value raises UnsupportedLLMProtocolError.

The model is read AFTER build_*_client has invoked require_vars, so a missing
SWAX_LLM_MODEL surfaces as MissingEnvironmentVariablesError rather than a bare
KeyError.
"""

import os

from .anthropic_adapter import AnthropicAdapter
from .build_anthropic_client import build_anthropic_client
from .build_openai_client import build_openai_client
from .errors import UnsupportedLLMProtocolError
from .llm_client import LLMClient
from .openai_adapter import OpenAIAdapter


def build_llm_client() -> LLMClient:
    """Build an LLMClient adapter selected by SWAX_LLM_PROTOCOL.

    Returns:
        An AnthropicAdapter or OpenAIAdapter wrapping the chosen SDK client and
        pinned to the model named by SWAX_LLM_MODEL.

    Raises:
        MissingEnvironmentVariablesError: when any SWAX_LLM_* variable is absent
            (surfaced by require_vars inside build_*_client).
        UnsupportedLLMProtocolError: when SWAX_LLM_PROTOCOL is neither
            "anthropic" nor "openai".
    """
    protocol = os.environ.get("SWAX_LLM_PROTOCOL")
    if protocol == "anthropic":
        return AnthropicAdapter(
            client=build_anthropic_client(),
            model=os.environ["SWAX_LLM_MODEL"],
        )
    if protocol == "openai":
        return OpenAIAdapter(
            client=build_openai_client(),
            model=os.environ["SWAX_LLM_MODEL"],
        )
    raise UnsupportedLLMProtocolError(protocol=protocol)


__all__: list[str] = ["build_llm_client"]
