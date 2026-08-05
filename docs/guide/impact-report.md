---
title: Impact Report
description: Markdown report on API change impact — risk, modified/affected endpoints, requirements, and checklist.
---

# Impact Report

The Impact Report is the output of `swax plan`. It's a Markdown document
echoed to stdout, summarizing the testing impact of API endpoint changes.

## Report sections

The report has six sections, in this order:

1. **Summary** — one-line human-readable summary.
2. **Risk** — overall risk level: `HIGH`, `MEDIUM`, or `LOW`.
3. **Modified Endpoints** — endpoint paths that changed.
4. **Affected Endpoints** — endpoint paths transitively affected via the
   traceability graph.
5. **Requirements** — testing requirements derived from the changes.
6. **Checklist** — actionable verification items.

## How `plan` builds it

1. Reads `.swax/config.yml` and loads the traceability graph.
2. Parses the **local baseline** specs.
3. **Shallow-clones** the spec repository fresh.
4. Per matching spec file pair, computes a structural diff and classifies
   endpoint changes (added / removed / modified).
5. Merges everything into a single `EndpointDiff`.
6. **No changes** → builds a `LOW`-risk
   `"No changes detected"` report and skips the LLM.
7. Otherwise maps the changed paths onto the graph via
   `find_affected_endpoints`, builds the system + user prompts, and runs a
   single `LLMClient.ask` call.
8. **Defensively parses** the LLM's JSON into an `ImpactReport`:
   - Strips prose and code fences around the JSON payload.
   - Validates the JSON shape against the contract.
   - Validates `risk` against `{HIGH, MEDIUM, LOW}` — an invalid value falls
     back to `MEDIUM` with a `WARNING` log.
9. Renders the report via `render_impact_report` and returns the Markdown.

## Diff classification

`EndpointDiff` aggregates:

- `added: list[str]` — endpoints in the current spec but not in the baseline.
- `removed: list[str]` — endpoints in the baseline but not in the current spec.
- `modified: dict[str, list[str]]` — path → list of change descriptions.

Helpers:

- `has_changes()` → `True` when any endpoint was added, removed, or modified.
- `changed_paths()` → sorted, deduplicated union of added, removed, and
  modified paths.

The diff sees methods/parameters/schemas for **analysis only** — classified
changes surface as paths with descriptions, **never** as method/schema-level
entries.

## Preconditions

- `.swax/config.yml` must exist (`init` must have been run).
- `.swax/traceability.yml` must exist (`discover` must have been run) —
  otherwise `TraceabilityGraphMissingError` is raised.
- LLM credentials must be present (`require_vars`).

## Errors

| Exception | Message |
| --- | --- |
| `MissingEnvironmentVariablesError` | `Missing env vars: ...` |
| `SpecParseError` | `Failed to parse <path>: <reason>` |
| `RepositoryCloneError` | `Failed to clone <url>: <reason>` |
| `SpecsNotFoundError` | `Specs directory not found at <path>` |
| `TraceabilityGraphMissingError` | `Traceability graph not found at <path> — run \`swax discover\` first` |
| `LLMRateLimitedError` | `LLM rate limited; retry later` |
| `LLMCallError` | `LLM call failed: <reason>` |
| `UnsupportedLLMProtocolError` | `Unsupported LLM protocol: <protocol>` |
| `LLMResponseParseError` | `LLM response parse failed: <reason>` |

## See also

- [Traceability graph](traceability-graph.md) — how affected endpoints are computed.
- [Commands / plan](commands.md#swax-plan) — CLI surface.
- [Architecture / applications cell](../architecture/cells/applications.md)
  — internal API (`run_plan`, `ImpactReport`, `render_impact_report`).
