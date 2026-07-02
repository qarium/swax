"""Logic tests for the swax.commands.discover cell (task 20).

run_discover is mocked at its use site (swax.commands.discover.discover.run_discover)
so no real config/spec/LLM work runs. The CliRunner drives the Click command. Two
scenarios verify the core contract: the six documented domain exceptions map to
click.ClickException (exit code 1, user-facing message), and a successful
run_discover exits 0 without issuing any prompts.

The discover handler accepts the Click ctx.obj (a SwaxContext under the real main
group) but intentionally does not read it, so a lightweight placeholder stands in
for the obj until the swax.cli cell is built (task 22). Only the six documented
domain exceptions are caught — generic Exception is never handled.
"""

import pathlib
import types

import pytest
from click.testing import CliRunner
from swax.commands.discover import discover
from swax.config import MissingEnvironmentVariablesError
from swax.llm import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from swax.openapi import SpecParseError

PATCH_RUN_DISCOVER = "swax.commands.discover.discover.run_discover"
# SwaxContext is not built until task 22 (swax/cli); the handler ignores ctx.obj,
# so a minimal placeholder mirrors the main-group forwarding shape.
_SWAX_CONTEXT_PLACEHOLDER = types.SimpleNamespace(env_file=pathlib.Path(".env"))


@pytest.mark.parametrize(
    ("exception", "expected_substring"),
    [
        (MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"]), "SWAX_LLM_TOKEN"),
        (SpecParseError(path=pathlib.Path("/p/bad.yaml"), reason="boom"), "Failed to parse"),
        (LLMRateLimitedError(reason="slow down"), "rate limited"),
        (LLMCallError(reason="500"), "LLM call failed"),
        (UnsupportedLLMProtocolError(protocol="ftp"), "Unsupported LLM protocol"),
        (LLMResponseParseError(reason="shape mismatch", excerpt="..."), "parse failed"),
    ],
)
def test_discover_handler_maps_domain_errors(mocker, exception, expected_substring):
    mocker.patch(PATCH_RUN_DISCOVER, side_effect=exception)
    runner = CliRunner()

    result = runner.invoke(discover, obj=_SWAX_CONTEXT_PLACEHOLDER)

    assert result.exit_code == 1
    assert expected_substring in result.output


def test_discover_handler_no_prompts(mocker):
    mock_run_discover = mocker.patch(PATCH_RUN_DISCOVER)
    runner = CliRunner()

    result = runner.invoke(discover, obj=_SWAX_CONTEXT_PLACEHOLDER)

    assert result.exit_code == 0
    mock_run_discover.assert_called_once_with(pathlib.Path.cwd())
