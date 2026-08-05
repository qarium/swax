---
title: swax/applications
description: Application-layer facade re-exporting use-cases (init, discover, plan) and their sub-cells.
---

# `swax/applications`

Application layer of Swax. Single facade for the project's use-cases —
consumers import types and cell-level practices (`init`, `discover`, `plan`)
from here via `Imports`, not from the sub-cells. The facade re-exports
`run_init_handler`, `run_discover_handler`, and `run_plan_handler` from their
sub-cells.

Use-cases are hexagonal orchestrators — **no business logic, no SDK calls
beyond delegated domain cells**. Domain exceptions propagate uncaught; mapping
to user-facing errors belongs to the command layer.

## Re-exports

| Symbol | Source cell | Alias |
| --- | --- | --- |
| `run_init` | `swax/applications/init` | `run_init_handler` |
| `run_discover` | `swax/applications/discover` | `run_discover_handler` |
| `run_plan` | `swax/applications/plan` | `run_plan_handler` |

---

## `swax/applications/init`

Application-layer use-case: orchestrates project initialization across three
domain cells. Contains no business logic — it only sequences calls.
`RepositoryCloneError` and `SpecsNotFoundError` propagate uncaught — the CLI
handler maps them. Logs `INFO` at start and end with project metadata; never
logs credentials.

### `run_init(repo_url, specs_location, download_path, project_root)`

Use-case "initialize project": persist configuration, clone the source
repository, and copy specs into the local project path.

- `repo_url`: clone URL of the source repository (collected by CLI prompts).
- `specs_location`: subdirectory inside the repository holding the specs.
- `download_path`: local destination for the copied specs (semantics of
  `SpecsConfig.location`).
- `project_root`: root of the Swax project — `.swax/` lives here.

Algorithm:

1. Assemble a `Config` from `GitConfig` and `SpecsConfig`.
2. Ensure `.swax/` exists and persist the config there.
3. Enter the `clone_specs` context to obtain the cloned specs path.
4. Inside the context, `copy_specs` from the clone into the local download
   path.

Requirements:

- Configuration is written **before** cloning — on clone failure the user
  still has `.swax/config.yml` to inspect.
- The `clone_specs` context guarantees temporary-directory cleanup on every
  outcome.

Constraints:

- Does **not** catch `RepositoryCloneError` / `SpecsNotFoundError`.
- Does **not** mutate `project_root` or `download_path`.

### Imports

- `Config`, `GitConfig`, `SpecsConfig`, `save_config` ← `swax/config`
  (practice: `project-config`)
- `clone_specs`, `RepositoryCloneError`, `SpecsNotFoundError` ← `swax/git`
  (practice: `specs-repository`)
- `ensure_swax_dir`, `copy_specs` ← `swax/fs` (practice: `project-layout`)

---

## `swax/applications/discover`

Application-layer use-case: full rebuild of the traceability graph via a
two-pass LLM analysis. The graph stores paths only and contains every endpoint
discovered in the parsed specs as a node — including endpoints with no inferred
dependencies. Edge deduplication is mandatory before saving.

`LLMCallError` and `LLMRateLimitedError` propagate uncaught — the CLI handler
maps them. Logs `INFO` at start/end, `DEBUG` for intermediate steps;
`SWAX_LLM_TOKEN` never in logs.

### LLM response parsing (provider-agnostic)

- Any prose or code fences around the JSON payload are stripped before parsing.
- `json.JSONDecodeError` is wrapped into `LLMResponseParseError` carrying a
  raw payload excerpt (first 200 chars) for diagnostics.
- The refine pass additionally unwraps a single-key `dependencies` envelope
  (`{"dependencies": {...}}`) — the model occasionally emits this form under
  multi-turn context despite the prompt contract — before applying the shape
  rule.
- The parsed shape is validated as `dict[str, list[str]]`; mismatched shapes
  are rejected via `LLMResponseParseError`.

### Dependency merging across the two passes

- The **first pass** contributes confident edges; the **refine pass**
  contributes resolved uncertain pairs. Both are merged into the final
  dependency map.
- The refine pass **overrides** the first pass only when it yields a
  **non-empty** adjacency list for a key; an empty refine list is treated as
  "no new information" so confident edges survive.
- Every endpoint extracted from the parsed specs is guaranteed to appear as a
  graph node (with an empty adjacency list when no dependency was inferred).
- Sources and targets **outside the endpoint universe** extracted from the
  parsed specs are dropped, honoring the prompt contract.

### `run_discover(project_root: pathlib.Path)`

Use-case "build traceability graph": full rebuild from scratch, ignoring any
existing graph.

- `project_root`: root of the Swax project — `.swax/config.yml` describes the
  specs, `.swax/traceability.yml` is overwritten.

Algorithm:

1. Validate LLM credentials via `require_vars`.
2. Read `Config` via `load_config` and locate the local specs root.
3. Discover spec files and extract endpoints + schema context from each.
4. **First LLM pass**: build system + user prompts, ask for dependency
   hypotheses across all endpoints.
5. **Refine pass**: build a refine prompt with schemas attached for ambiguous
   pairs, re-ask in multi-turn mode.
6. Merge confident edges with resolved uncertain pairs; guarantee every
   extracted endpoint appears as a graph node; drop sources/targets outside
   the endpoint universe.
7. Build the `TraceabilityGraph` from the merged dependencies, deduplicate,
   persist.

Requirements:

- Always builds a **fresh** graph — existing `.swax/traceability.yml` is
  ignored.
- Endpoint order is deterministic across runs (`discover_specs` returns sorted
  output).
- LLM responses are parsed defensively per the rules above.
- The persisted graph contains every endpoint extracted from the parsed specs,
  including endpoints with no inferred dependencies (persisted with an empty
  adjacency list).

Constraints:

- Does **not** catch `LLMCallError` / `LLMRateLimitedError`.
- Does **not** store schemas in the graph — paths only.
- Does **not** embed filesystem paths or credentials into prompts.
- Does **not** introduce paths outside the endpoint universe.

### Imports

- `load_config`, `require_vars`, `Config` ← `swax/config`
  (practices: `project-config`, `environment`)
- `discover_specs`, `parse_spec`, `extract_paths`, `extract_schemas` ←
  `swax/openapi` (practices: `parsing`, `extraction`)
- `LLMClient`, `build_llm_client`, `LLMCallError`, `LLMRateLimitedError`,
  `LLMResponseParseError` ← `swax/llm` (practice: `llm-transport`)
- `build_graph_system_prompt`, `build_graph_user_prompt`,
  `build_refine_user_prompt` ← `swax/prompts`
  (practice: `traceability-llm-prompts`)
- `TraceabilityGraph`, `save_traceability` ← `swax/traceability`
  (practice: `graph-lifecycle`)

---

## `swax/applications/plan`

Application-layer use-case: generate an Impact Report by diffing baseline vs
fresh specs, mapping changes onto the traceability graph, and asking the LLM
once. The graph stores paths only; the diff sees methods/schemas for analysis
but the report carries paths with change descriptions. Domain exceptions
propagate uncaught — the CLI handler maps them.

`TraceabilityGraphMissingError` is raised when `.swax/traceability.yml` is
absent (hint: run `discover`). Logs `INFO` at start/end, `DEBUG` for
intermediate steps; `SWAX_LLM_TOKEN` never in logs.

### LLM response parsing (provider-agnostic)

- Strip prose/code fences around the JSON payload before parsing.
- `json.JSONDecodeError` is wrapped into `LLMResponseParseError` with a raw
  payload excerpt.
- The parsed shape is validated against the Impact Report contract; mismatch →
  `LLMResponseParseError`.
- The `risk` field is validated against `{HIGH, MEDIUM, LOW}`; an invalid
  value falls back to `MEDIUM` (WARNING log).

### `run_plan(project_root: pathlib.Path) -> markdown: str`

Use-case "plan": analyze differences between baseline and fresh specifications
and produce an Impact Report.

- `project_root`: root of the Swax project — `.swax/config.yml` describes
  specs/repo, `.swax/traceability.yml` is read.
- `markdown`: the Impact Report rendered as Markdown for stdout.

Algorithm:

1. Validate LLM credentials via `require_vars`.
2. Read `Config` via `load_config`.
3. Load the traceability graph via `load_traceability`; if the file is absent,
   raise `TraceabilityGraphMissingError`.
4. Clone the repository via `clone_specs` (context manager) and parse the
   fresh specs.
5. Parse the baseline specs from the local root.
6. For each matching spec file pair, compute `diff_specs` then
   `classify_endpoint_changes`; merge into one `EndpointDiff`.
7. If `EndpointDiff` reports **no changes**, build a no-change `ImpactReport`
   (summary "No changes detected", risk `LOW`) and **skip the LLM**.
8. Otherwise map the changed paths onto the graph via
   `find_affected_endpoints` and extract the relevant graph context.
   If the affected set or graph context exceeds a reasonable threshold, trim
   to the most relevant entries (changed paths first, then nearest
   dependents) and log a WARNING that the LLM context was truncated. Then
   build the system + user prompts.
9. Call `LLMClient` once to ask for the report, defensively parse JSON into
   an `ImpactReport`, validate risk (fallback `MEDIUM`).
10. Render via `render_impact_report` and return the Markdown.

Requirements:

- The repository clone is cleaned up on every outcome.
- Baseline and fresh specs are matched by relative path.
- Risk is constrained to `{HIGH, MEDIUM, LOW}` with a `MEDIUM` fallback.
- `SWAX_LLM_TOKEN` never appears in logs or the returned Markdown.

Constraints:

- Does **not** catch `LLMCallError` / `LLMRateLimitedError` /
  `LLMResponseParseError`.
- Does **not** store schemas or methods as separate report paths — paths with
  change descriptions only.
- Does **not** print to stdout — return the Markdown; the CLI handler echoes
  it.

### Imports

- `load_config`, `require_vars`, `Config` ← `swax/config`
  (practices: `project-config`, `environment`)
- `clone_specs`, `RepositoryCloneError`, `SpecsNotFoundError` ← `swax/git`
  (practice: `specs-repository`)
- `discover_specs`, `parse_spec`, `diff_specs`, `classify_endpoint_changes`,
  `EndpointDiff` ← `swax/openapi` (practices: `parsing`, `diff`)
- `load_traceability`, `TraceabilityGraph`, `find_affected_endpoints`,
  `TraceabilityGraphMissingError` ← `swax/traceability`
  (practices: `graph-lifecycle`, `affected-endpoints`)
- `build_impact_report_system_prompt`, `build_impact_report_user_prompt` ←
  `swax/prompts` (practice: `impact-report-prompts`)
- `build_llm_client`, `LLMClient`, `LLMCallError`, `LLMRateLimitedError`,
  `LLMResponseParseError` ← `swax/llm` (practice: `llm-transport`)

### `ImpactReport(summary, risk, modified, affected, requirements, checklist)`

Structured LLM output for the Impact Report.

| Property | Type | Description |
| --- | --- | --- |
| `summary` | `str` | One-line human-readable summary of the change impact. |
| `risk` | `str` | Overall risk level — `HIGH`, `MEDIUM`, or `LOW` (validated by `run_plan`). |
| `modified` | `list[str]` | Endpoint paths that changed. |
| `affected` | `list[str]` | Endpoint paths transitively affected via the graph. |
| `requirements` | `list[str]` | Testing requirements derived from the changes. |
| `checklist` | `list[str]` | Actionable verification checklist items. |

### `render_impact_report(report: ImpactReport) -> markdown: str`

Renders an `ImpactReport` into the Markdown template for stdout.

- Follows the report template: Summary, Risk, Modified, Affected,
  Requirements, Checklist.
- Renders the no-change report identically to any other report.

Constraints:

- Pure transformation — **no I/O, no LLM calls**.
- Does **not** synthesize content not present in `report`.

## See also

- [Traceability graph](../../guide/traceability-graph.md) — graph model and format.
- [Impact Report](../../guide/impact-report.md) — report shape.
- [Architecture / commands cell](commands.md) — handlers that map use-case
  exceptions.
