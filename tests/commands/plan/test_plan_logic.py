"""Logic tests for the swax.commands.plan cell.

run_plan is mocked at its use site (swax.commands.plan.plan.run_plan) so no real
config/spec/graph/LLM work runs. The CliRunner drives the Click command. The
scenarios verify the core contract: the nine documented domain exceptions map to
click.ClickException (exit code 1, user-facing message, no SWAX_LLM_TOKEN leak),
and a successful run_plan echoes the Markdown Impact Report and exits 0 without
issuing any prompts.

The plan handler accepts the Click ctx.obj (a SwaxContext under the real main
group) but intentionally does not read it, so a lightweight placeholder stands
in for the obj. Only the nine documented domain exceptions are caught — generic
Exception is never handled.
"""

import pathlib
import types

import pytest
from click.testing import CliRunner
from swax.commands.plan import plan
from swax.config import MissingEnvironmentVariablesError
from swax.git import RepositoryCloneError, SpecsNotFoundError
from swax.llm import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from swax.openapi import SpecParseError
from swax.traceability import TraceabilityGraphMissingError

PATCH_RUN_PLAN = "swax.commands.plan.plan.run_plan"
# The handler ignores ctx.obj; a minimal placeholder mirrors the main-group
# forwarding shape.
_SWAX_CONTEXT_PLACEHOLDER = types.SimpleNamespace(env_file=pathlib.Path(".env"))


@pytest.mark.parametrize(
    ("exception", "expected_substring"),
    [
        (MissingEnvironmentVariablesError(missing=["SWAX_LLM_BASE_URL"]), "SWAX_LLM_BASE_URL"),
        (SpecParseError(path=pathlib.Path("/p/bad.yaml"), reason="boom"), "Failed to parse"),
        (RepositoryCloneError(url="https://example.com/specs.git", reason="auth"), "Failed to clone"),
        (SpecsNotFoundError(path=pathlib.Path("/p/specs")), "Specs directory not found"),
        (
            TraceabilityGraphMissingError(path=pathlib.Path(".swax/traceability.yml")),
            "Traceability graph not found",
        ),
        (LLMRateLimitedError(reason="slow down"), "rate limited"),
        (LLMCallError(reason="500"), "LLM call failed"),
        (UnsupportedLLMProtocolError(protocol="ftp"), "Unsupported LLM protocol"),
        (LLMResponseParseError(reason="shape mismatch", excerpt="..."), "parse failed"),
    ],
)
def test_plan_handler_maps_all_nine_domain_errors(mocker, exception, expected_substring):
    mocker.patch(PATCH_RUN_PLAN, side_effect=exception)
    runner = CliRunner()

    result = runner.invoke(plan, obj=_SWAX_CONTEXT_PLACEHOLDER)

    assert result.exit_code == 1
    assert expected_substring in result.output
    assert "SWAX_LLM_TOKEN" not in result.output


def test_plan_handler_echoes_markdown_and_maps_missing_graph(mocker):
    """Success echoes the report; the missing-graph error renders the discover hint."""
    runner = CliRunner()

    # case a — success echoes the Markdown report.
    mocker.patch(PATCH_RUN_PLAN, return_value="# Impact Report\n\n**Summary:** ok\n")
    result_ok = runner.invoke(plan, obj=_SWAX_CONTEXT_PLACEHOLDER)
    assert result_ok.exit_code == 0
    assert "# Impact Report" in result_ok.output

    # case b — TraceabilityGraphMissingError maps to the discover hint.
    mocker.patch(
        PATCH_RUN_PLAN,
        side_effect=TraceabilityGraphMissingError(path=pathlib.Path(".swax/traceability.yml")),
    )
    result_missing = runner.invoke(plan, obj=_SWAX_CONTEXT_PLACEHOLDER)
    assert result_missing.exit_code == 1
    assert "Traceability graph not found" in result_missing.output
    assert "swax discover" in result_missing.output


def test_plan_handler_no_prompts(mocker):
    mock_run_plan = mocker.patch(PATCH_RUN_PLAN, return_value="# Impact Report\n")
    runner = CliRunner()

    result = runner.invoke(plan, obj=_SWAX_CONTEXT_PLACEHOLDER)

    assert result.exit_code == 0
    mock_run_plan.assert_called_once_with(pathlib.Path.cwd())
