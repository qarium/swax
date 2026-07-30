# Discover command — Click handler for the `discover` command

## Domain

Registration and invocation template for the `discover` Click command. Target audience: cell `swax/cli/` (registers the command on the `main` group via `main.add_command(discover)`).

The command is thin — only error mapping. Application logic (spec parsing, LLM analysis, graph assembly) is delegated to `run_discover` (cell `applications/discover/`). Unlike `init`, `discover` has no interactive prompts — all inputs come from `.swax/config.yml` and the environment.

---

## Command registration

`discover` is a decorated `@click.command` callback. Registration on the main group:

```python
from swax.cli import main
from swax.commands.discover import discover

main.add_command(discover)
```

Consumer conventions:
- The command takes no CLI options and has no prompts.
- The context is passed via `@click.pass_obj` — `SwaxContext` from the `cli/` cell.
- Requires a pre-loaded `.env` (the `main` group callback has already invoked `load_env`).

---

## Command execution

On `swax discover`, the command:

1. Receives `SwaxContext` via `@click.pass_obj`.
2. Resolves `project_root = pathlib.Path.cwd()`.
3. Delegates to `run_discover(project_root)`.
4. Catches domain exceptions from `config/`, `openapi/`, `llm/` and maps them to `click.ClickException`.

---

## Error handling

All domain exceptions are mapped to `click.ClickException` with clear messages:

| Exception | Message |
|-----------|---------|
| MissingEnvironmentVariablesError | Missing env vars: {missing} |
| SpecParseError | Failed to parse {path}: {reason} |
| LLMRateLimitedError | LLM rate limited; retry later |
| LLMCallError | LLM call failed: {reason} |
| UnsupportedLLMProtocolError | Unsupported LLM protocol: {protocol} |
| LLMResponseParseError | LLM response parse failed: {reason} |

Exit codes: 0 — success, 1 — failure (Click default for `ClickException`).

The command does NOT retry rate-limited calls and does NOT log `SWAX_LLM_TOKEN` in error messages.

---

## Testing

Test via `click.testing.CliRunner`, mocking `run_discover` at its import point:

```python
from pathlib import Path

from click.testing import CliRunner


def test_discovers_graph_on_success(mocker, tmp_path):
    mocker.patch("swax.commands.discover.run_discover")
    runner = CliRunner()
    result = runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
    assert result.exit_code == 0


def test_discovers_maps_missing_env_vars(mocker):
    def raise_missing(project_root):
        raise MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"])

    mocker.patch("swax.commands.discover.run_discover", side_effect=raise_missing)
    runner = CliRunner()
    result = runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
    assert result.exit_code == 1
    assert "SWAX_LLM_TOKEN" in result.output
```

Never call the live LLM API in tests — always mock `run_discover`.
