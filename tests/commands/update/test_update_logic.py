"""Logic tests for the swax.commands.update cell.

run_update is mocked at its use site (swax.commands.update.update.run_update) so
no real config/clone/spec/LLM work runs. The CliRunner drives the Click command.
The scenarios verify the core contract: the ten documented domain exceptions map
to click.ClickException (exit code 1, user-facing message per the pinned table,
no SWAX_LLM_TOKEN value leak), and a successful run_update echoes the update
summary and exits 0 without issuing any prompts.

The update handler accepts the Click ctx.obj (a SwaxContext under the real main
group) but intentionally does not read it, so a real SwaxContext instance stands
in for the obj. Only the ten documented domain exceptions are caught — generic
Exception is never handled.
"""

import pathlib

import pytest
from click.testing import CliRunner
from swax.applications import GraphRebuildFailedError
from swax.cli import SwaxContext
from swax.commands.update import update
from swax.config import MissingEnvironmentVariablesError
from swax.fs import UnsafeSpecsLocationError
from swax.git import RepositoryCloneError, SpecsNotFoundError
from swax.llm import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from swax.openapi import SpecParseError

PATCH_RUN_UPDATE = "swax.commands.update.update.run_update"


@pytest.fixture
def swax_context() -> SwaxContext:
    return SwaxContext(env_file=pathlib.Path(".env"))


def test_update_command_echoes_summary(mocker, swax_context):
    mock_run_update = mocker.patch(PATCH_RUN_UPDATE, return_value="Specs are up to date.")
    runner = CliRunner()

    result = runner.invoke(update, obj=swax_context)

    assert result.exit_code == 0
    assert "Specs are up to date." in result.output
    mock_run_update.assert_called_once_with(pathlib.Path.cwd())


@pytest.mark.parametrize(
    ("exception", "expected_message"),
    [
        (UnsafeSpecsLocationError(path=pathlib.Path("/x")), "Refusing to mirror into /x"),
        (GraphRebuildFailedError(reason="r"), "Graph rebuild failed: r; specs restored."),
        (RepositoryCloneError(url="u", reason="r"), "Failed to clone u: r"),
        (SpecsNotFoundError(path=pathlib.Path("p")), "Specs not found at p"),
        (MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"]), "Missing env vars: SWAX_LLM_TOKEN"),
        (SpecParseError(path=pathlib.Path("s"), reason="r"), "Failed to parse s: r"),
        (LLMRateLimitedError(reason="r"), "LLM rate limited; retry later"),
        (LLMCallError(reason="r"), "LLM call failed: r"),
        (UnsupportedLLMProtocolError(protocol="x"), "Unsupported LLM protocol: x"),
        (LLMResponseParseError(reason="r", excerpt="e"), "LLM response parse failed: r"),
    ],
)
def test_update_maps_domain_errors(mocker, swax_context, exception, expected_message):
    mocker.patch(PATCH_RUN_UPDATE, side_effect=exception)
    runner = CliRunner()

    result = runner.invoke(update, obj=swax_context)

    assert result.exit_code == 1
    assert expected_message in result.output
    # The token NAME may appear in the missing-vars message; its VALUE never does.
    assert "test-token" not in result.output


def test_update_does_not_catch_generic_exception(mocker, swax_context):
    mocker.patch(PATCH_RUN_UPDATE, side_effect=ValueError("unexpected"))
    runner = CliRunner()

    result = runner.invoke(update, obj=swax_context)

    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)
