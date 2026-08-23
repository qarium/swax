---
title: swax/prompts
description: LLM prompt builders for the traceability graph construction (two-pass), the change-impact report (single-turn), and the incremental graph rebuild scenarios.
---

# `swax/prompts`

LLM prompt builders for the traceability graph construction (two-pass), the
change-impact report (single-turn), and the incremental graph rebuild
(single-turn) scenarios.

Every routine returns a fully-formed prompt string ready for `LLMClient.ask` /
`ask_multi_turn`. Prompts request structured JSON output; the consumer parses
the response defensively. Prompts **never embed filesystem paths, tokens, or
secrets** — only the data passed as arguments.

## Traceability graph prompts

### `build_graph_system_prompt() -> prompt: str`

Builds the system prompt that instructs the LLM to act as an API dependency
analyst.

- `prompt`: the system message reused across both passes of `run_discover`.

Requirements:

- Defines the LLM role: analyze API endpoints and propose dependency edges
  between paths.
- Mandates the output contract: a JSON object mapping source path to a list of
  dependent paths.
- Forbids prose around JSON — the response must be parseable as JSON.
- States explicitly that the graph operates on **paths only** — no HTTP
  methods.

Constraints:

- **No parameters** — the system prompt is constant for the `discover`
  use-case.
- No endpoint list, no schemas — those go into user prompts.

### `build_graph_user_prompt(endpoints: list[str]) -> prompt: str`

Builds the first-pass user prompt: lists endpoints and asks for dependency
hypotheses.

- `endpoints`: API path templates collected by `extract_paths` across all
  parsed specs.
- `prompt`: the user message for the initial `LLMClient.ask` call.

Algorithm:

1. Render `endpoints` as a JSON array.
2. Instruct the LLM to return a JSON object with two keys: `dependencies`
   (mapping `source_path` to list of `dependent_paths`) and `uncertain` (list
   of uncertain dependency pairs as `"/source -> /target"` strings).
3. The consumer routes uncertain pairs into the refine pass via
   `build_refine_user_prompt`.

Requirements:

- Output format matches what the consumer's first-pass JSON parser expects: a
  dict with exactly two keys — `dependencies` (`dict[str, list[str]]`) and
  `uncertain` (`list[str]`).
- Endpoint order in the prompt follows the sorted order from `extract_paths`
  for determinism.
- The LLM flags uncertain pairs in the `uncertain` array so the consumer can
  route them to the refine pass.

Constraints:

- **Do not** inline schemas here — they belong to the refine pass.

### `build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> prompt: str`

Builds the refine-pass user prompt: provides schemas for ambiguous pairs and
asks for final dependency decisions.

- `ambiguous_pairs`: pairs flagged as uncertain in the first-pass response
  (e.g. `"/users -> /orders"`).
- `schemas`: schema definitions from `extract_schemas`, attached as context.
- `prompt`: the user message for the final turn of `LLMClient.ask_multi_turn`.

Algorithm:

1. Render `ambiguous_pairs` as a JSON array.
2. Render `schemas` as a JSON object keyed by schema name.
3. Instruct the LLM to return a consolidated JSON object covering all pairs,
   without introducing paths outside the provided endpoint universe.

Requirements:

- The full schema dict is passed; the LLM selects the schemas relevant to the
  pairs.
- Output contract is **identical** to `build_graph_user_prompt` so the
  consumer reuses the same parser.

Constraints:

- **Do not** re-list all endpoints — the multi-turn context already carries
  them.
- Forbid introducing paths outside the provided endpoint universe.

## Impact report prompts

### `build_impact_report_system_prompt() -> prompt: str`

Builds the system prompt that instructs the LLM to act as an API change impact
analyst.

- `prompt`: the system message for the single-turn `LLMClient.ask` call in
  `run_plan`.

Requirements:

- Defines the LLM role: assess the testing impact of API endpoint changes.
- Mandates the output contract: JSON with `summary`, `risk`, `modified`,
  `affected`, `requirements`, `checklist`.
- Fixes allowed risk values to `HIGH`, `MEDIUM`, `LOW`.
- Forbids prose around JSON — the response must be parseable as JSON.

Constraints:

- **No parameters** — the system prompt is constant for the `plan` use-case.
- No endpoint data or graph — those go into the user prompt.
- **Never embed** filesystem paths, tokens, or secrets.

### `build_impact_report_user_prompt(added, removed, modified, affected, graph_context) -> prompt: str`

Builds the user prompt: structured change context plus affected endpoints and
the relevant graph portion.

- `added` / `removed`: endpoint path lists.
- `modified`: path → change descriptions.
- `affected`: transitively affected endpoints.
- `graph_context`: relevant graph edges (path → dependencies), sliced from
  the traceability graph for the affected paths.
- `prompt`: the user message for `LLMClient.ask`.

Algorithm:

1. Render `added` / `removed` / `affected` as JSON arrays.
2. Render `modified` / `graph_context` as JSON objects.
3. Instruct the LLM to return the Impact Report JSON contract from the system
   prompt.

Requirements:

- Output format matches the parser in `run_plan`.
- Endpoint order follows the sorted order supplied by the caller.

Constraints:

- **Do not** truncate silently — the caller trims before calling if the
  context is large.
- **Never embed** filesystem paths, tokens, or secrets.

## Incremental graph rebuild prompts

The `swax update` scenario: revise an existing dependency graph from the
spec-file changes, in a single turn.

### `build_incremental_graph_system_prompt() -> prompt: str`

Constant system prompt for the incremental revision.

Requirements:

- Role: "API dependency analyst revising an existing dependency graph."
- Output contract: a JSON object mapping source path to a list of dependent
  paths — **the full updated graph, not a delta**.
- Universe rule: cover every endpoint of the updated universe provided in the
  user prompt; no paths outside it.
- JSON-only rule: the response must be parseable as JSON — no prose, code
  fences, or commentary.
- Paths-only rule: the graph operates on paths only, not HTTP methods — two
  endpoints sharing a path are a single node.

Constraints:

- **No parameters**; no endpoint data — those go into the user prompt.

### `build_incremental_graph_user_prompt(existing_edges, diff_added, diff_removed, diff_modified, added_endpoints, added_schemas) -> prompt: str`

Renders the revision input: the current graph, the endpoint-level change set,
the new-specs content, and the computed endpoint universe.

- `existing_edges`: the graph as loaded (`dict[str, list[str]]`, insertion
  order preserved).
- `diff_added` / `diff_removed`: endpoint path lists; `diff_modified`: path →
  change descriptions.
- `added_endpoints` / `added_schemas`: endpoints and schema definitions of
  the newly added spec files.

Algorithm:

1. Render the graph, the change set (`added` / `removed` / `modified`), and
   the new-specs payload (`endpoints` / `schemas`) as JSON.
2. Compute the universe
   `sorted((set(existing_edges) - set(diff_removed)) | set(diff_added) | set(added_endpoints))`
   and render it as a JSON array.
3. Instruct the LLM to return the complete updated dependency mapping
   covering exactly every endpoint of the universe.

Constraints:

- No truncation; the universe formula is identical to the consumer-side
  filter in `run_update` — do not drift it.
- **Never embed** filesystem paths, tokens, or secrets.

## See also

- [Architecture / llm cell](llm.md) — transports that consume the prompts.
- [Architecture / applications/discover cell](applications.md#swaxapplicationsdiscover) —
  two-pass scenario.
- [Architecture / applications/plan cell](applications.md#swaxapplicationsplan) —
  single-turn scenario.
- [Architecture / applications/update cell](applications.md#swaxapplicationsupdate) —
  incremental rebuild scenario.
