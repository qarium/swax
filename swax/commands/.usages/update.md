# Update command — Click handler for the `update` command

## Domain

Registration and invocation template for the `update` Click command. Target audience: cell
`swax/cli/` (registers the command on the `main` group via `main.add_command(update)`).

The command is thin — only error mapping and echo. Application logic (mirroring,
conditional graph rebuild, the transaction) is delegated to `run_update` (cell
`applications/update/`). The command is fully non-interactive — all inputs come from
`.swax/config.yml` and the environment.

## Command registration

`update` is a decorated `@click.command` callback. Registration on the main group:

```python
from swax.cli import main
from swax.commands.update import update

main.add_command(update)
```

Consumer conventions:
- The command takes no CLI options and has no prompts.
- The context is passed via `@click.pass_obj` — `SwaxContext` from the `cli/` cell.
- Requires a pre-loaded `.env` (the `main` group callback has already invoked `load_env`).

## Command execution

On `swax update`, the command:

1. Receives `SwaxContext` via `@click.pass_obj`.
2. Resolves `project_root = pathlib.Path.cwd()`.
3. Delegates to `run_update(project_root)` and echoes the returned summary.
4. Catches domain exceptions and maps them to `click.ClickException`.

## Error handling

| Exception | Message |
|-----------|---------|
| UnsafeSpecsLocationError | Refusing to mirror into {path} |
| RepositoryCloneError | Failed to clone {url}: {reason} |
| SpecsNotFoundError | Specs not found at {path} |
| MissingEnvironmentVariablesError | Missing env vars: {missing} |
| SpecParseError | Failed to parse {path}: {reason} |
| LLMRateLimitedError | LLM rate limited; retry later |
| LLMCallError | LLM call failed: {reason} |
| UnsupportedLLMProtocolError | Unsupported LLM protocol: {protocol} |
| LLMResponseParseError | LLM response parse failed: {reason} |
| GraphRebuildFailedError | Graph rebuild failed: {reason}; specs restored. |

Exit codes: 0 — success, 1 — failure (Click default for `ClickException`).

Config-reading failures are not mapped — they surface raw, consistent with the rest of the
command family. The command does NOT retry rate-limited calls and does NOT log
`SWAX_LLM_TOKEN` in error messages.

## Testing

Test via `click.testing.CliRunner`, mocking `run_update` at its import point:

```python
from pathlib import Path

from click.testing import CliRunner


def test_update_echoes_summary(mocker):
    mocker.patch("swax.commands.update.run_update", return_value="Specs are up to date.")
    runner = CliRunner()
    result = runner.invoke(update, obj=SwaxContext(env_file=Path(".env")))
    assert result.exit_code == 0
    assert "Specs are up to date." in result.output
```

Never call the live LLM API or a real remote in tests — always mock `run_update`.
