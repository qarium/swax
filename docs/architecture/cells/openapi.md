---
title: swax/openapi
description: Parsing of OpenAPI/Swagger specifications, extraction of paths and schemas, structural diffing, and endpoint change classification.
---

# `swax/openapi`

Parsing of OpenAPI/Swagger specifications and extraction of paths and schemas
for the traceability graph, plus structural diffing of two dereferenced specs
and classification of endpoint/schema changes.

The graph operates on **paths only** — no HTTP methods, no resource abstraction
(architectural rule: minimal abstraction). Swagger 2.0 and OpenAPI 3.x are
handled transparently — both store paths under `paths`. The diff sees
methods/parameters/schemas for analysis only — classified changes surface as
paths with descriptions, **never** as method/schema-level entries.

## Parsing & extraction

### `parse_spec(spec_path: pathlib.Path) -> spec: dict`

Parses a specification file into a fully dereferenced dict (all non-cyclic
`$ref` inlined).

- `spec_path`: path to a `.yaml` / `.yml` / `.json` spec file.
- `spec`: dereferenced specification containing paths and schemas.

Algorithm:

1. Read the file and parse it via Prance's formats helper.
2. Construct a Prance reference resolver over the parsed spec (strict mode
   off, resolve all reference types).
3. Configure the resolver to **terminate reference cycles** by emitting a
   `$ref` marker instead of raising — prevents failure on self-referential
   and mutually-recursive schemas.
4. Return the dereferenced specification.
5. On any parser failure, raise `SpecParseError` with the path and original
   reason.

Requirements:

- Non-cyclic `$ref` is resolved in memory — downstream code never resolves
  those references manually.
- Cyclic `$ref` terminates at the cycle point with a `$ref` marker preserving
  structural information.

Constraints:

- RAM usage scales with spec size and reference count (known limitation,
  accepted).
- The Prance post-resolve spec validator is **intentionally bypassed** — it
  rejects otherwise valid recursive schemas after dereferencing.

### `extract_paths(spec: dict) -> paths: list[str]`

Collects API path templates from a parsed specification, discarding HTTP
methods.

- `spec`: dereferenced dict (output of `parse_spec`).
- `paths`: sorted list of path templates (e.g. `/users`, `/users/{id}`).

Algorithm:

1. Read the `paths` mapping from `spec`.
2. Return its keys as a sorted list.

Requirements:

- Result feeds the traceability graph nodes directly — no method-level
  entries.

### `extract_schemas(spec: dict) -> schemas: dict`

Collects schema definitions from a parsed specification for LLM context
enrichment.

- `spec`: dereferenced dict.
- `schemas`: mapping of schema name to its definition (already inlined by the
  parser).

Algorithm:

1. If `spec` exposes OpenAPI 3.x `components`, return its schemas sub-mapping.
2. Otherwise return the Swagger 2.0 `definitions` sub-mapping.

Requirements:

- Transparently distinguishes OpenAPI 3.x (`components.schemas`) from
  Swagger 2.0 (`definitions`).
- Schemas are used **only** by `build_refine_user_prompt` — never stored in
  the graph.

### `discover_specs(root: pathlib.Path) -> specs: list[pathlib.Path]`

Enumerates spec files under `root` by extension and a lightweight content
heuristic.

- `root`: directory to search (typically the local specs path from
  `SpecsConfig`).
- `specs`: sorted list of spec file paths.

Algorithm:

1. Walk `root` recursively.
2. Keep files with extension `.yaml` / `.yml` / `.json`.
3. Keep files whose head contains an `openapi` or `swagger` key.

Requirements:

- The heuristic is cheap — full parsing happens later via `parse_spec`.
- Returned order is deterministic (sorted).

## Diffing & classification

### `diff_specs(base: dict, current: dict) -> diff: DeepDiff`

Computes a structural diff between two dereferenced specifications.

- `base`: baseline (local) spec dict — output of `parse_spec`.
- `current`: fresh (cloned repo) spec dict — output of `parse_spec`.
- `diff`: a `DeepDiff` result consumed by `classify_endpoint_changes`.

Algorithm:

1. Build a `DeepDiff` over `base` and `current` with `ignore_order` and the
   cutoff option from `deepdiff`.
2. Return the result unchanged — classification happens in
   `classify_endpoint_changes`.

Requirements:

- Both inputs are fully dereferenced (Prance already inlined `$ref` via
  `parse_spec`).
- List order is ignored — endpoint order is not significant.

Constraints:

- **Do not classify changes here** — this routine only computes the raw
  structural diff.
- Avoid `verbose_level=2` in the production path.

### `classify_endpoint_changes(diff: DeepDiff) -> changes: EndpointDiff`

Classifies a raw structural diff into endpoint-level changes.

- `diff`: `DeepDiff` result from `diff_specs`.
- `changes`: an `EndpointDiff` aggregating added, removed, and modified
  endpoints with schema detail.

Algorithm:

1. Walk the diff change sets (`dictionary_item_added`, `dictionary_item_removed`,
   `values_changed`) by their path strings. These are the deepdiff categories
   produced by `diff_specs`.
2. Paths under the `paths` key become endpoint changes: added / removed /
   modified.
3. Paths under the `components`/`definitions` keys are schema changes —
   because `$ref` is already dereferenced, each affected endpoint surfaces the
   change directly; attribute it to that endpoint.
4. Aggregate multiple changes on the same path into a single `modified` entry
   with a list of descriptions.
5. Return the `EndpointDiff`.

Requirements:

- Swagger 2.0 (`definitions`) and OpenAPI 3.x (`components.schemas`) handled
  transparently.
- Modified entries carry human-readable change descriptions for the Impact
  Report.

Constraints:

- **Do not** emit method-level or schema-level entries as separate paths —
  paths only.
- **Do not** introduce endpoints outside the union of base and current path
  keys.

### `EndpointDiff(added, removed, modified)`

Classified change result between baseline and current specifications.

| Property | Type | Description |
| --- | --- | --- |
| `added` | `list[str]` | Endpoint paths present in the current spec but not in the baseline. |
| `removed` | `list[str]` | Endpoint paths present in the baseline but not in the current spec. |
| `modified` | `dict[str, list[str]]` | Endpoint path → list of human-readable change descriptions. |

Methods:

| Method | Return | Description |
| --- | --- | --- |
| `has_changes()` | `bool` | True when any endpoint was added, removed, or modified. |
| `changed_paths()` | `list[str]` | Union of added, removed, and modified endpoint paths — sorted and deduplicated. Deterministic; each path appears once. |

## Errors

| Exception | Cause |
| --- | --- |
| `SpecParseError(path: pathlib.Path, reason: str)` | Raised by `parse_spec` when parsing or dereferencing a specification fails. Carries the offending spec file path and the original Prance error message. |

## See also

- [Traceability graph](../../guide/traceability-graph.md) — what `extract_paths` feeds.
- [Impact Report](../../guide/impact-report.md) — what `EndpointDiff` feeds.
- [Architecture / applications/plan cell](applications.md#swaxapplicationsplan) —
  consumes the diff API.
