---
title: Configuration
description: Environment variables for the LLM transport and the project configuration file.
---

# Configuration

Swax reads configuration from two sources:

1. **Environment variables** (the `.env` file or your shell) — LLM credentials
   and provider settings.
2. **`.swax/config.yml`** — project coordinates: the spec repository and the
   local download path. Written by `swax init`, read by `swax discover` and
   `swax plan`.

## Environment variables

Put them in a `.env` file (loaded via the `--env-file` option) or export them
in your shell. **Shell values take precedence over the file.**

| Variable | Meaning |
| --- | --- |
| `SWAX_LLM_MODEL` | Model name (e.g. `claude-sonnet-4-6`, `gpt-4o`). |
| `SWAX_LLM_PROTOCOL` | Provider identifier: `anthropic` or `openai`. |
| `SWAX_LLM_BASE_URL` | LLM API base URL **without** a `/v1` or `/v2` version segment — the SDK appends it. |
| `SWAX_LLM_TOKEN` | LLM API token. **Never written to logs or error messages.** |

Rules enforced at validation time:

- An **unknown** `SWAX_LLM_PROTOCOL` raises `InvalidLLMProtocolError`.
- A `SWAX_LLM_BASE_URL` ending with `/v1` or `/v2` raises `InvalidLLMBaseURLError`.
- Empty or whitespace-only values count as **missing** and raise
  `MissingEnvironmentVariablesError` when LLM credentials are required
  (`discover`, `plan`).

Validation is **lazy**: it runs only inside use-cases that need LLM
credentials. `swax init` does **not** validate them.

## `.swax/config.yml`

Shape:

```yaml
git:
  url: https://example.com/specs.git
  location: specs
specs:
  type: openapi        # openapi | swagger
  location: downloaded
```

| Field | Description |
| --- | --- |
| `git.url` | Clone URL consumed by `clone_specs`. Private repos use git credential helpers — **never embed credentials in the URL**. |
| `git.location` | Subdirectory inside the repository where specs live. |
| `specs.type` | Declared spec format. Informational — the parser detects the actual version at parse time. |
| `specs.location` | Local path where `copy_specs` writes the downloaded specs. |

`save_config` writes the file with stable YAML (sorted keys, deterministic
output) so the diff between runs stays clean.

## Next step

Run through the [Quickstart](quickstart.md) to build your first traceability graph.
