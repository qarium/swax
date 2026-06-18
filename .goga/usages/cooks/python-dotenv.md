# python-dotenv — Environment Loading

## Domain

Patterns for loading `.env` files into the process environment. Target audience: the `config/` cell and the CLI entry point.

Swax exposes `--env-file <path>` on the CLI. All `SWAX_*` variables must be loaded from the file before any command handler runs.

---

## Loading Order

Load `.env` early — at the start of the Click `main` group callback, before subcommands execute. Use `override=False` to respect variables already set in the shell.

```python
import os
import pathlib

from dotenv import load_dotenv


def load_env(env_file: pathlib.Path) -> None:
    if env_file.exists():
        load_dotenv(env_file, override=False)
```

`override=False` lets developers override values during testing or in CI by exporting real environment variables.

---

## Required Variables

Validate required `SWAX_*` variables explicitly with a clear error message when missing.

```python
REQUIRED_VARS = ("SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN")


def require_vars() -> dict[str, str]:
    values = {name: os.environ.get(name) for name in REQUIRED_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise MissingEnvironmentVariablesError(missing=missing)
    return values
```

Run `require_vars()` lazily — only for commands that need the LLM (`discover`, later `update`). The `init` command does not require LLM credentials.

---

## CLI Wiring

Call `load_env` from the Click group callback so every subcommand sees the loaded environment.

```python
@main.group()
@click.option("--env-file", type=click.Path(path_type=pathlib.Path), default=".env")
@click.pass_context
def main(ctx: click.Context, env_file: pathlib.Path) -> None:
    load_env(env_file)
    ctx.obj = SwaxContext(env_file=env_file)
```

---

## Validation

`SWAX_LLM_PROTOCOL` accepts only `anthropic` or `openai`. Validate at the configuration boundary.

```python
ALLOWED_PROTOCOLS = ("anthropic", "openai")


def parse_protocol(value: str) -> str:
    if value not in ALLOWED_PROTOCOLS:
        raise InvalidLLMProtocolError(value=value, allowed=ALLOWED_PROTOCOLS)
    return value
```

---

## Base URL Validation

`SWAX_LLM_BASE_URL` must not end with a version segment (e.g. `/v1`, `/v2`). Validate at config load.

```python
def parse_base_url(value: str) -> str:
    if value.rstrip("/").endswith(("/v1", "/v2")):
        raise InvalidLLMBaseURLError(value=value)
    return value
```

---

## Testing

Set real environment variables in tests; do not write `.env` files. Use `monkeypatch.setenv` and `monkeypatch.delenv` to control state per test.

```python
def test_require_vars_raises_when_missing(monkeypatch) -> None:
    for name in REQUIRED_VARS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(MissingEnvironmentVariablesError):
        require_vars()
```