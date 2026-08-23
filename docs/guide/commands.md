---
title: Commands
description: CLI surface — init, discover, plan, update, the global --env-file option, and exit codes.
---

# Commands

Swax exposes four subcommands on the `swax` Click group. All commands share
the global `--env-file` option and the `SwaxContext` pass object.

## Global: `--env-file`

```bash
swax --env-file <path> <subcommand>
```

- Default: `.env` (relative to the current working directory).
- A **missing** file is silently ignored — real shell variables still apply.
- **Shell variables take precedence over file values** (`override=False`).

`load_env` runs in the top-level group callback **before** any subcommand, so
the environment is always populated when a handler runs.

## `swax init`

Initialize a project from a remote spec repository.

```bash
swax --env-file .env init
```

Interactive prompts:

1. **Repository URL** — git source of the specifications.
2. **Path to specs inside the repo** — the subdirectory to copy.
3. **Local download path** — where the specs land in the project.

Internally `init` writes `.swax/config.yml`, shallow-clones the repository
(`depth=1`), and copies the specs into the local download path. **Configuration
is written before cloning** so you can inspect it even if the clone fails.

| Exit code | Cause |
| --- | --- |
| `0` | Success. |
| `1` | `RepositoryCloneError` — `Failed to clone <url>: <reason>`. |
| `1` | `SpecsNotFoundError` — `Specs not found at <path>`. |

`init` does **not** validate `SWAX_LLM_*` variables — it doesn't need LLM
credentials.

## `swax discover`

Rebuild the traceability graph from scratch.

```bash
swax --env-file .env discover
```

Reads `.swax/config.yml` and the environment (no prompts). Discovers and parses
the local specs, runs a two-pass LLM analysis, deduplicates edges, and
overwrites `.swax/traceability.yml`.

**Always builds a fresh graph** — the existing `traceability.yml` is ignored.

| Exit code | Cause |
| --- | --- |
| `0` | Success. |
| `1` | `MissingEnvironmentVariablesError` — `Missing env vars: ...`. |
| `1` | `SpecParseError` — `Failed to parse <path>: <reason>`. |
| `1` | `LLMRateLimitedError` — `LLM rate limited; retry later`. |
| `1` | `LLMCallError` — `LLM call failed: <reason>`. |
| `1` | `UnsupportedLLMProtocolError` — `Unsupported LLM protocol: <protocol>`. |
| `1` | `LLMResponseParseError` — `LLM response parse failed: <reason>`. |

The command does **not** retry rate-limited calls and does **not** log
`SWAX_LLM_TOKEN`.

## `swax plan`

Generate a Markdown Impact Report from spec changes.

```bash
swax --env-file .env plan
```

Reads `.swax/config.yml`, the environment, and `.swax/traceability.yml`
(produced by `swax discover`). Parses the local baseline specs, shallow-clones
the spec repository fresh, classifies the endpoint diff
(added / removed / modified), maps the changed endpoints onto the
traceability graph to find transitively affected endpoints, and runs a
single-turn LLM analysis.

With **no changes**, it skips the LLM and prints a `LOW`-risk
"No changes detected" report.

Report sections: **Summary, Risk (`HIGH` / `MEDIUM` / `LOW`), Modified
Endpoints, Affected Endpoints, Requirements, Checklist**.

| Exit code | Cause |
| --- | --- |
| `0` | Success. |
| `1` | `MissingEnvironmentVariablesError` — `Missing env vars: ...`. |
| `1` | `SpecParseError` — `Failed to parse <path>: <reason>`. |
| `1` | `RepositoryCloneError` — `Failed to clone <url>: <reason>`. |
| `1` | `SpecsNotFoundError` — `Specs directory not found at <path>`. |
| `1` | `TraceabilityGraphMissingError` — `Traceability graph not found at <path> — run \`swax discover\` first`. |
| `1` | `LLMRateLimitedError` — `LLM rate limited; retry later`. |
| `1` | `LLMCallError` — `LLM call failed: <reason>`. |
| `1` | `UnsupportedLLMProtocolError` — `Unsupported LLM protocol: <protocol>`. |
| `1` | `LLMResponseParseError` — `LLM response parse failed: <reason>`. |

## `swax update`

Mirror the local specs to the remote state and rebuild the traceability
graph conditionally, as one transaction.

```bash
swax --env-file .env update
```

Reads `.swax/config.yml` and the environment (no prompts; the project root is
the current working directory). Shallow-clones the spec repository fresh,
classifies the byte-level file diff between the local specs directory and the
clone, and then branches:

- **No changes** — prints `Specs are up to date.` Nothing is touched, no LLM.
- **Removals only** — the specs are mirrored and the graph is pruned
  deterministically (endpoints of removed spec files) **without an LLM call**;
  the summary ends with `Traceability graph: rebuilt`. If no graph file
  exists, the graph work is skipped and the summary has no status line.
- **Added/updated files** — `SWAX_LLM_*` credentials are validated **before
  any mutation**; then the graph is revised incrementally with a single-turn
  LLM analysis (`Traceability graph: rebuilt`) or, when no graph exists,
  built from scratch by the same logic as `swax discover`
  (`Traceability graph: built`).

The summary lists `Added:` / `Updated:` / `Removed:` groups (empty groups
omitted) plus the graph status line. The remote clone is the source of truth —
local spec edits are overwritten silently. A failure during the rebuild
restores the previous specs (and the previous graph) before exiting.

| Exit code | Cause |
| --- | --- |
| `0` | Success. |
| `1` | `UnsafeSpecsLocationError` — `Refusing to mirror into <path>`. |
| `1` | `GraphRebuildFailedError` — `Graph rebuild failed: <reason>; specs restored.`. |
| `1` | `RepositoryCloneError` — `Failed to clone <url>: <reason>`. |
| `1` | `SpecsNotFoundError` — `Specs not found at <path>`. |
| `1` | `MissingEnvironmentVariablesError` — `Missing env vars: ...`. |
| `1` | `SpecParseError` — `Failed to parse <path>: <reason>`. |
| `1` | `LLMRateLimitedError` — `LLM rate limited; retry later`. |
| `1` | `LLMCallError` — `LLM call failed: <reason>`. |
| `1` | `UnsupportedLLMProtocolError` — `Unsupported LLM protocol: <protocol>`. |
| `1` | `LLMResponseParseError` — `LLM response parse failed: <reason>`. |

The command does **not** log `SWAX_LLM_TOKEN`.

## See also

- [Quickstart](../getting-started/quickstart.md) — `init → discover → plan` walkthrough.
- [Project layout](project-layout.md) — what each file means.
- [Architecture / CLI cell](../architecture/cells/cli.md) — Click group internals.
