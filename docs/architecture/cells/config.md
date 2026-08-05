---
title: swax/config
description: Project configuration model, .env loading, and SWAX_* environment variable validation.
---

# `swax/config`

Project configuration and environment. Holds the project model and validates
`SWAX_*` credentials for LLM access.

All pydantic models use `kw_only`. Relative imports inside the cell.
`SWAX_LLM_TOKEN` never appears in logs.

## Configuration models

### `Config(git: GitConfig, specs: SpecsConfig)`

Root configuration model of a Swax project, persisted to `.swax/config.yml`.

- `git`: git repository coordinates for the source specifications.
- `specs`: local layout of downloaded specifications.

Constraints:

- Both fields are required — a project without git or specs is invalid.

### `GitConfig(url: str, location: str)`

Coordinates of the remote git repository holding API specifications.

- `url`: clone URL consumed by `clone_specs`.
- `location`: subdirectory inside the repository where specs live.

Constraints:

- URL must **not** embed credentials — private repositories are served via
  git credential helpers.

### `SpecsConfig(type: Literal['swagger', 'openapi'], location: str)`

Local layout of downloaded specifications.

- `type`: declared spec format (`swagger` or `openapi`). Informational only —
  the parser detects the actual version at parse time.
- `location`: local path where `copy_specs` writes specs.

## Environment routines

### `load_env(env_file: pathlib.Path)`

Loads `.env` into the process environment before any command handler runs.

- `env_file`: path to the dotenv file from the `--env-file` option.

Algorithm:

1. If the file does not exist, return without error.
2. Load it so **real shell variables keep precedence** over file values.

Requirements:

- Missing file is **not** an error — return silently.
- Real environment variables take precedence over file values.

### `require_vars() -> vars: dict[str, str]`

Validates that all mandatory `SWAX_*` variables are present in the environment.

- `vars`: mapping of variable name to its value, returned for caller
  convenience.

Algorithm:

1. Read each mandatory variable name from the environment.
2. Treat empty and whitespace-only values as missing.
3. If any are missing, raise `MissingEnvironmentVariablesError`.
4. Otherwise return the name-to-value mapping.

Requirements:

- **Lazy validation** — called only from use-cases that need LLM credentials
  (`run_discover`). `run_init` bypasses it.
- Whitespace-only values count as missing.
- Mandatory set: `SWAX_LLM_MODEL`, `SWAX_LLM_PROTOCOL`, `SWAX_LLM_BASE_URL`,
  `SWAX_LLM_TOKEN`.

### `parse_protocol(value: str) -> protocol: str`

Validates `SWAX_LLM_PROTOCOL` as a supported provider identifier.

- `value`: raw value from the environment.
- `protocol`: validated protocol string, unchanged.

Algorithm:

1. Compare `value` against the accepted protocol set.
2. On mismatch, raise `InvalidLLMProtocolError`.
3. Otherwise return `value` unchanged.

Constraints:

- Values outside `("anthropic", "openai")` raise `InvalidLLMProtocolError`.

### `parse_base_url(value: str) -> base_url: str`

Rejects `SWAX_LLM_BASE_URL` that includes a version segment.

- `value`: raw value from the environment.
- `base_url`: validated URL, unchanged.

Algorithm:

1. Strip trailing slashes from `value`.
2. If the result ends with a version segment, raise `InvalidLLMBaseURLError`.
3. Otherwise return the stripped URL.

Constraints:

- URL ending with `/v1` or `/v2` raises `InvalidLLMBaseURLError`.

## Persistence

### `load_config(path: pathlib.Path) -> config: Config`

Reads `.swax/config.yml` and validates it into a `Config` model.

- `path`: path to the configuration file.
- `config`: parsed and validated configuration.

Algorithm:

1. Read the file as UTF-8 text.
2. Parse YAML with the safe loader.
3. Validate the resulting structure into the `Config` model.

Requirements:

- File is read as UTF-8.
- Parsing uses a **safe** YAML loader — no arbitrary deserialization.
- Structure is validated against the `Config` model before returning.

### `save_config(config: Config, path: pathlib.Path)`

Persists `Config` to `.swax/config.yml` deterministically.

- `config`: configuration to write.
- `path`: destination file path.

Algorithm:

1. Convert the model into YAML-safe primitives.
2. Create parent directories as needed.
3. Dump YAML in a stable form (key order preserved, Unicode allowed, block
   style).
4. Write text as UTF-8.

Requirements:

- Parent directories are created as needed.
- Output is **stable across runs** for clean diffs.

## Errors

| Exception | Cause |
| --- | --- |
| `MissingEnvironmentVariablesError(missing: list[str])` | Raised by `require_vars` when one or more mandatory `SWAX_*` variables are missing. |
| `InvalidLLMProtocolError(value: str, allowed: tuple[str, ...])` | Raised by `parse_protocol` on an unsupported `SWAX_LLM_PROTOCOL` value. |
| `InvalidLLMBaseURLError(value: str)` | Raised by `parse_base_url` when `SWAX_LLM_BASE_URL` contains a version segment (`/v1`, `/v2`). |

## See also

- [Configuration](../../getting-started/configuration.md) — end-user guide to
  `.env` and `.swax/config.yml`.
