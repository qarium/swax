---
title: swax/commands
description: Command-layer facade re-exporting CLI handlers (init, discover, plan) and their sub-cells.
---

# `swax/commands`

Command layer of Swax. Single facade for CLI handlers — consumers register
commands and pull cell-level practices (`init`, `discover`, `plan`) from here
via `Imports`, not from the sub-cells. The facade re-exports `init_handler`,
`discover_handler`, and `plan_handler` from their sub-cells.

Handlers stay **thin** — only argument parsing and exception mapping to
`click.ClickException`. All orchestration lives in the application layer.

## Re-exports

| Symbol | Source cell | Alias |
| --- | --- | --- |
| `init` | `swax/commands/init` | `init_handler` |
| `discover` | `swax/commands/discover` | `discover_handler` |
| `plan` | `swax/commands/plan` | `plan_handler` |

---

## `swax/commands/init`

Click handler for the `init` command: prompts the user, delegates to
`run_init`, and maps domain exceptions.

### `init(ctx: click.Context)`

- `ctx`: Click context whose `obj` is a `SwaxContext` carrying the env-file
  path.

Algorithm:

1. Resolve `ctx.obj` as `SwaxContext` via `@click.pass_obj`.
2. Prompt for `repo_url`, `specs_location`, `download_path`.
3. Resolve `project_root` from the current working directory.
4. Delegate to `run_init` inside a `try`.
5. Map `RepositoryCloneError` and `SpecsNotFoundError` to
   `click.ClickException`.

Requirements:

- **Prompts are the sole source of user input** — no command-line options for
  these values.
- Exit code 0 on success, 1 on any `ClickException`.

Constraints:

- Does **not** catch generic `Exception` — only the two domain exceptions.
- Does **not** log credentials.

### Imports

- `SwaxContext` ← `swax/cli` (practice: `cli-facade`)
- `run_init` ← `swax/applications` (practice: `init`)
- `RepositoryCloneError`, `SpecsNotFoundError` ← `swax/git`
  (practice: `specs-repository`)

---

## `swax/commands/discover`

Click handler for the `discover` command: delegates to `run_discover` and maps
domain exceptions. No interactive prompts — all inputs come from
`.swax/config.yml` and the environment.

### `discover(ctx: click.Context)`

- `ctx`: Click context whose `obj` is a `SwaxContext`.

Algorithm:

1. Resolve `ctx.obj` as `SwaxContext` via `@click.pass_obj`.
2. Resolve `project_root` from the current working directory.
3. Delegate to `run_discover` inside a `try`.
4. Map every documented domain exception to `click.ClickException`:
   `MissingEnvironmentVariablesError`, `SpecParseError`,
   `LLMRateLimitedError`, `LLMCallError`, `UnsupportedLLMProtocolError`,
   `LLMResponseParseError`.

Requirements:

- No interactive prompts.
- Exit code 0 on success, 1 on any `ClickException`.

Constraints:

- Does **not** catch generic `Exception`.
- Does **not** retry rate-limited calls.
- `SWAX_LLM_TOKEN` never appears in any error message.

### Imports

- `SwaxContext` ← `swax/cli` (practice: `cli-facade`)
- `run_discover` ← `swax/applications` (practice: `discover`)
- `MissingEnvironmentVariablesError` ← `swax/config` (practice: `environment`)
- `SpecParseError` ← `swax/openapi` (practice: `parsing`)
- `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError`,
  `UnsupportedLLMProtocolError` ← `swax/llm` (practice: `llm-transport`)

---

## `swax/commands/plan`

Click handler for the `plan` command: delegates to `run_plan`, echoes the
report, and maps domain exceptions to user-facing errors.

### `plan(ctx: click.Context)`

- `ctx`: Click context whose `obj` is a `SwaxContext`.

Algorithm:

1. Resolve `ctx.obj` as `SwaxContext` via `@click.pass_obj`.
2. Resolve `project_root` from the current working directory.
3. Delegate to `run_plan` inside a `try`.
4. Echo the returned Markdown to stdout.
5. Map every documented domain exception to `click.ClickException`:
   `MissingEnvironmentVariablesError`, `SpecParseError`,
   `RepositoryCloneError`, `SpecsNotFoundError`,
   `TraceabilityGraphMissingError`, `LLMRateLimitedError`, `LLMCallError`,
   `UnsupportedLLMProtocolError`, `LLMResponseParseError`.

Requirements:

- No interactive prompts.
- Exit code 0 on success, 1 on any `ClickException`.

Constraints:

- Does **not** catch generic `Exception`.
- Does **not** retry rate-limited calls.
- `SWAX_LLM_TOKEN` never appears in any error message or echoed output.

### Imports

- `SwaxContext` ← `swax/cli` (practice: `cli-facade`)
- `run_plan` ← `swax/applications` (practice: `plan`)
- `MissingEnvironmentVariablesError` ← `swax/config` (practice: `environment`)
- `SpecParseError` ← `swax/openapi` (practice: `parsing`)
- `RepositoryCloneError`, `SpecsNotFoundError` ← `swax/git`
  (practice: `specs-repository`)
- `TraceabilityGraphMissingError` ← `swax/traceability`
  (practice: `affected-endpoints`)
- `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError`,
  `UnsupportedLLMProtocolError` ← `swax/llm` (practice: `llm-transport`)

## See also

- [Commands](../../guide/commands.md) — end-user CLI reference.
- [Architecture / applications cell](applications.md) — use-case orchestrators.
