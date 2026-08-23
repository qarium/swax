---
title: Cells reference
description: Per-cell contracts, public API, and consumer practices for every Swax cell.
---

# Cells reference

Each Swax cell has a `CODEMANIFEST` describing its contract and a `.usages/`
directory documenting how to consume it. The pages below summarize the public
API and link into the architectural details.

## CLI layer

- [**`swax/cli`**](cli.md) — top-level Click group (`main`), `--env-file`
  option, and `SwaxContext` pass object.

## Command layer (facades + handlers)

- [**`swax/commands`**](commands.md) — facade re-exporting `init_handler`,
  `discover_handler`, `plan_handler`, `update_handler`.
  - Subcells: `commands/init`, `commands/discover`, `commands/plan`,
    `commands/update`.

## Application layer (facades + use-cases)

- [**`swax/applications`**](applications.md) — facade re-exporting
  `run_init_handler`, `run_discover_handler`, `run_plan_handler`,
  `run_update_handler` (+ `GraphRebuildFailedError`).
  - Subcells: `applications/init`, `applications/discover`,
    `applications/plan`, `applications/update`.

## Domain cells

| Cell | Responsibility |
| --- | --- |
| [**`swax/config`**](config.md) | Project configuration model, `.env` loading, `SWAX_*` validation. |
| [**`swax/fs`**](fs.md) | `.swax/` directory management, spec copying, and transactional spec mirroring. |
| [**`swax/git`**](git.md) | Read-only git repository cloning (context manager). |
| [**`swax/openapi`**](openapi.md) | OpenAPI/Swagger parsing, extraction, structural diffing, classification. |
| [**`swax/llm`**](llm.md) | Provider-agnostic LLM transport (Anthropic + OpenAI adapters). |
| [**`swax/prompts`**](prompts.md) | Prompt builders for graph construction, impact report, and incremental graph rebuild. |
| [**`swax/traceability`**](traceability.md) | Graph model, YAML persistence, transitive-impact traversal. |

## Architectural rules (cross-cutting)

- The graph operates on **paths only** — no HTTP methods, no resource
  abstraction.
- Use-cases are hexagonal orchestrators — **no business logic**, no SDK calls
  beyond delegated domain cells.
- Domain exceptions propagate **uncaught** through the application layer;
  mapping to user-facing errors belongs to the command layer.
- `SWAX_LLM_TOKEN` **never appears in logs or error messages**.
- Pydantic models use `kw_only`.
- Relative imports inside each cell.
- Adapters receive the SDK client and model via **constructor injection** —
  for testability via mock at import point.

For full conventions see [Conventions](../conventions.md).
