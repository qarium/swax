---
title: Quickstart
description: Initialize a project, discover the traceability graph, and generate an impact report.
---

# Quickstart

This walkthrough runs the three Swax commands end-to-end:
`init → discover → plan`. By the end you will have a traceability graph and a
Markdown impact report on disk.

## 0. Prerequisites

- [Swax installed](installation.md).
- A `.env` file with the four `SWAX_LLM_*` variables (see
  [Configuration](configuration.md)).

## 1. Initialize the project

```bash
swax --env-file .env init
```

`init` interactively prompts for:

1. **Repository URL** — git source of the specifications.
2. **Path to specs inside the repo** — the subdirectory to copy.
3. **Local download path** — where the specs land in the project.

It writes `.swax/config.yml`, shallow-clones the repository (`depth=1`), and
copies the specs into the local download path.

## 2. Discover the traceability graph

```bash
swax --env-file .env discover
```

`discover` rebuilds `.swax/traceability.yml` from scratch. It:

1. Parses the local specs.
2. Runs a two-pass LLM analysis:
   - **First pass** — initial dependency hypotheses.
   - **Refine pass** — schema-informed re-analysis of uncertain pairs.
3. Merges confident edges with resolved uncertain pairs.
4. Guarantees every discovered endpoint appears as a graph node.
5. Deduplicates and writes deterministic YAML.

The graph stores **paths only** — no HTTP methods, no resource abstraction.

## 3. Generate an Impact Report

```bash
swax --env-file .env plan
```

`plan` analyzes spec changes since the last `discover` and prints a Markdown
Impact Report to stdout. It:

1. Parses the local baseline specs.
2. Shallow-clones the spec repository fresh.
3. Classifies the endpoint diff (added / removed / modified).
4. Maps changed endpoints onto the traceability graph to find transitively
   affected endpoints.
5. Runs a single-turn LLM analysis.

With **no changes**, it skips the LLM and prints a `LOW`-risk
"No changes detected" report.

The report contains **Summary, Risk (`HIGH` / `MEDIUM` / `LOW`), Modified
Endpoints, Affected Endpoints, Requirements, and Checklist** sections.

## Result

After this walkthrough your project contains:

```
.swax/
  config.yml          # written by init
  traceability.yml    # written by discover
<download_path>/      # the copied specifications
```

## Next steps

- [Commands reference](../guide/commands.md) — full CLI surface, options, exit codes.
- [Traceability graph](../guide/traceability-graph.md) — graph model and file format.
- [Impact Report](../guide/impact-report.md) — report shape and usage.
