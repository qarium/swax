---
title: Architecture overview
description: Hexagonal layering of Swax — CLI, command handlers, application use-cases, and domain cells.
---

# Architecture overview

Swax follows a **hexagonal (ports & adapters) layering**. Each layer has a
single responsibility, and dependencies point **inward** — domain cells know
nothing about the layers above them.

## Layers

```
                ┌───────────────────────────────────────┐
   external ───▶│  cli/                                 │
                │   Click group, --env-file, SwaxContext│
                └─────────────────┬─────────────────────┘
                                  │
                ┌─────────────────▼─────────────────────┐
                │  commands/                            │
                │   thin Click handlers — exception     │
                │   mapping only                        │
                └─────────────────┬─────────────────────┘
                                  │
                ┌─────────────────▼─────────────────────┐
                │  applications/                        │
                │   use-case orchestrators — sequencing │
                │   of domain cells, no business logic  │
                └─────────────────┬─────────────────────┘
                                  │
   ┌──────────────────────────────┼─────────────────────────────┐
   │                              │                             │
┌──▼─────┐  ┌────────┐  ┌─────────▼──────┐  ┌─────────┐  ┌──────▼────┐
│ config │  │  git   │  │   openapi      │  │   llm   │  │   prompts │
└──┬─────┘  └────┬───┘  └────────────────┘  └────┬────┘  └───────────┘
   │             │                               │
   │       ┌─────▼─────┐                         │
   │       │    fs     │                         │
   │       └───────────┘                         │
   │                                             │
   └──────────────────┬──────────────────────────┘
                      │
                ┌─────▼──────┐
                │traceability│
                └────────────┘
```

| Layer | Cells | Responsibility |
| --- | --- | --- |
| **CLI** | `swax/cli` | Top-level Click group, `--env-file`, `SwaxContext` pass object. |
| **Command** | `swax/commands` (+ `init`, `discover`, `plan`, `update`) | Thin Click handlers — argument parsing and exception mapping to `click.ClickException`. No orchestration. |
| **Application** | `swax/applications` (+ `init`, `discover`, `plan`, `update`) | Hexagonal orchestrators — sequence domain cells, no business logic, no SDK calls beyond delegated domain cells. Domain exceptions propagate uncaught. |
| **Domain** | `swax/config`, `swax/fs`, `swax/git`, `swax/openapi`, `swax/llm`, `swax/prompts`, `swax/traceability` | Pure domain logic — parsing, transport, models, persistence. |

## Dependency direction

**Domain cells never import from CLI, command, or application layers.** They
are pure and independently testable. The application layer orchestrates them;
the command layer maps their exceptions; the CLI provides the entry point.

A notable structural rule: **`commands/` imports from `cli/`** (for
`SwaxContext`), but `cli/` does **not** import from `commands/` in
`__init__.py` — registration happens lazily in `cli/__main__.py` to keep the
contract acyclic.

## Facade pattern

`swax/commands` and `swax/applications` are **facade cells** — each re-exports
the handlers / use-cases of its sub-cells:

```yaml
# swax/commands/CODEMANIFEST (excerpt)
->init_handler: {}
->discover_handler: {}
->plan_handler: {}
->update_handler: {}
```

Consumers register commands or pull cell-level practices from the facade via
`Imports`, not from the sub-cells.

## See also

- [Cells reference](cells/index.md) — per-cell contracts and consumer guides.
- [Conventions](conventions.md) — code-writing and testing conventions.
