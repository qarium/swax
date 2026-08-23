---
title: Swax
description: Traceability graph builder for API endpoint dependencies from OpenAPI / Swagger specifications.
---

# Swax

Swax is a tool for building **traceability graphs** of API endpoint dependencies
from OpenAPI / Swagger specifications, using a two-pass LLM analysis. Given a
spec repository, it infers which API paths depend on which other paths and
persists the result as a deterministic graph.

> **Status:** Alpha. The `init`, `discover`, `plan`, and `update` commands are
> the currently implemented surface.

## What you can do

- **Initialize** a project from a remote spec repository (`swax init`).
- **Discover** the API dependency graph via a two-pass LLM analysis
  (`swax discover`).
- **Plan** testing impact from spec changes with an LLM-generated Markdown
  report (`swax plan`).
- **Update** local specs to the remote state and incrementally rebuild the
  graph (`swax update`).

## Where to go next

- [Installation](getting-started/installation.md) — set up the tool.
- [Configuration](getting-started/configuration.md) — `.env`, `.swax/config.yml`.
- [Quickstart](getting-started/quickstart.md) — `init → discover → plan` walkthrough.
- [Commands reference](guide/commands.md) — full CLI surface.
- [Architecture overview](architecture/overview.md) — cells, layers, dependency graph.

## Project layout

```
.swax/
  config.yml          # written by `swax init`
  traceability.yml    # written by `swax discover`, pruned/rebuilt by `swax update`
<download_path>/      # the copied specifications (re-mirrored by `swax update`)
```

## License

BSD-3-Clause. See `LICENSE` in the repository root.
