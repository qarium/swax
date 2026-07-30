# Environment — `.env` and `SWAX_*` variables

## Domain

Templates for loading `.env` and validating `SWAX_*` environment variables. Target audience: cell `swax/cli/` (the CLI entry point loads `.env` before running commands) and cells that need LLM credentials (`applications/discover/`, `swax/llm/`).

All variables carry the `SWAX_` prefix. The `.env` file is loaded optionally — real environment variables take precedence.

---

## Required variables

| Variable | Purpose |
|----------|---------|
| `SWAX_LLM_MODEL` | model name (e.g., `"claude-sonnet-4-6"` or `"gpt-4o"`) |
| `SWAX_LLM_PROTOCOL` | `"anthropic"` or `"openai"` |
| `SWAX_LLM_BASE_URL` | base URL **without** the version segment (`/v1`) |
| `SWAX_LLM_TOKEN` | access token for the LLM API |

---

## Loading `.env`

Run early — in the Click group callback, before subcommands:

```python
from pathlib import Path

from swax.config import load_env


def setup_cli(env_file: Path) -> None:
    load_env(env_file)
```

`load_env` uses `override=False`: variables already set in the shell are not overwritten. This lets developers and CI override values without editing `.env`.

---

## Lazy validation

`require_vars()` returns a mapping only if all required variables are present; otherwise it raises `MissingEnvironmentVariablesError`. Call it lazily — only in use cases that need the LLM:

```python
from swax.config import require_vars


def before_llm_call() -> dict[str, str]:
    return require_vars()
```

`init` does not need LLM credentials and must not call `require_vars`.

---

## Value validators

`parse_protocol` and `parse_base_url` validate the value format before SDK clients are constructed:

```python
from swax.config import parse_protocol, parse_base_url

protocol = parse_protocol(os.environ["SWAX_LLM_PROTOCOL"])
base_url = parse_base_url(os.environ["SWAX_LLM_BASE_URL"])
```

Both raise domain exceptions (`InvalidLLMProtocolError`, `InvalidLLMBaseURLError`) with a clear message that the CLI maps to `click.ClickException`.

---

## Testing

In tests, set variables via `monkeypatch.setenv` and remove them via `monkeypatch.delenv` — do not write `.env` files.
