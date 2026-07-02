"""Logic tests for the swax.commands.init cell (task 19).

run_init is mocked at its use site (swax.commands.init.init.run_init) so no real
clone, copy, or filesystem mutation runs. The CliRunner drives the Click command
with piped prompt input. Three scenarios verify the core contract: prompted
values reach run_init, and the two documented domain exceptions map to
click.ClickException (exit code 1, user-facing message). No generic Exception is
caught — only RepositoryCloneError and SpecsNotFoundError.
"""

import pathlib

from click.testing import CliRunner
from swax.commands.init import init
from swax.git import RepositoryCloneError, SpecsNotFoundError

PATCH_RUN_INIT = "swax.commands.init.init.run_init"
PROMPT_INPUT = "u\nl\n./p\n"


class TestInitHandler:
    def test_init_invokes_run_init_with_prompted_values(self, mocker):
        mock_run_init = mocker.patch(PATCH_RUN_INIT)
        runner = CliRunner()

        result = runner.invoke(init, input=PROMPT_INPUT)

        assert result.exit_code == 0
        mock_run_init.assert_called_once_with("u", "l", pathlib.Path("./p"), pathlib.Path.cwd())

    def test_init_handler_maps_repository_clone_error(self, mocker):
        mock_run_init = mocker.patch(PATCH_RUN_INIT)
        mock_run_init.side_effect = RepositoryCloneError(url="https://example.com/repo.git", reason="auth failed")
        runner = CliRunner()

        result = runner.invoke(init, input=PROMPT_INPUT)

        assert result.exit_code == 1
        assert "Failed to clone" in result.output
        assert "auth failed" in result.output

    def test_init_handler_maps_specs_not_found_error(self, mocker):
        mock_run_init = mocker.patch(PATCH_RUN_INIT)
        mock_run_init.side_effect = SpecsNotFoundError(path=pathlib.Path("/missing/specs"))
        runner = CliRunner()

        result = runner.invoke(init, input=PROMPT_INPUT)

        assert result.exit_code == 1
        assert "Specs not found at" in result.output
        assert "/missing/specs" in result.output
