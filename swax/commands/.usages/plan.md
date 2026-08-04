# Plan command — Click handler for the `plan` command

## Domain

Registration and invocation template for the `plan` Click command. Target audience: cell
`swax/cli/` (registers the command on the `main` group via `main.add_command(plan)`).

The command is thin — only echo + error mapping. Application logic (clone, diff, mapping, LLM,
render) is delegated to `run_plan` (cell `applications/plan/`). No interactive prompts.

## Command registration

```python
from swax.cli import main
from swax.commands.plan import plan

main.add_command(plan)
```

Consumer conventions:
- The command takes no CLI options and has no prompts.
- The context is passed via `@click.pass_obj` — `SwaxContext` from the `cli/` cell.
- Requires a pre-loaded `.env` (the `main` group callback has already invoked `load_env`).

## Command execution

On `swax plan`, the command:
1. Receives `SwaxContext` via `@click.pass_obj`.
2. Resolves `project_root = pathlib.Path.cwd()`.
3. Delegates to `run_plan(project_root)` and echoes the returned Markdown to stdout.
4. Catches domain exceptions and maps them to `click.ClickException`.

## Error handling

| Exception | Message |
|---|---|
| MissingEnvironmentVariablesError | Missing env vars: {missing} |
| SpecParseError | Failed to parse {path}: {reason} |
| RepositoryCloneError | Failed to clone {url}: {reason} |
| SpecsNotFoundError | Specs directory not found: {path} |
| TraceabilityGraphMissingError | Traceability graph not found at {path} — run `swax discover` first |
| LLMRateLimitedError | LLM rate limited; retry later |
| LLMCallError | LLM call failed: {reason} |
| UnsupportedLLMProtocolError | Unsupported LLM protocol: {protocol} |
| LLMResponseParseError | LLM response parse failed: {reason} |

Exit codes: 0 — success, 1 — failure (Click default for `ClickException`).

## Testing

Test via `click.testing.CliRunner`, mocking `run_plan` at its import point. Assert `exit_code`
and echoed Markdown. Never call the live LLM API — always mock `run_plan`.
