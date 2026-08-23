---
title: swax/traceability
description: Traceability graph model, YAML persistence, transitive-impact traversal, and the missing-graph domain error.
---

# `swax/traceability`

In-memory model and persistence of the traceability graph.

The graph stores **paths only** — no HTTP methods, no resource abstraction.
Edge deduplication is mandatory before saving. All pydantic models use
`kw_only`. Relative imports inside the cell.

## Model

### `TraceabilityGraph(edges: dict[str, list[str]])`

In-memory model of the traceability graph: API path → list of dependent paths.

- `edges`: mapping of source path to its dependencies. Defaults to empty dict.

Requirements:

- Accumulates edges during `run_discover` via `add_edge`.
- Caller invokes `deduplicate` before saving to produce stable output.

Properties:

| Property | Type | Description |
| --- | --- | --- |
| `edges` | `dict[str, list[str]]` | The underlying adjacency mapping. Exposed for serialization; consumers mutate it via `add_edge`, not by direct assignment. |

Methods:

#### `add_edge(source: str, target: str)`

Records a single dependency: `source` depends on `target`.

- `source`: the path that depends on another.
- `target`: the path it depends on.

Requirements:

- Permits **duplicates** at insert time — resolved later by `deduplicate`.
- **Self-loops** (`source == target`) are permitted at insert time and
  filtered by `deduplicate`.

#### `deduplicate()`

Removes duplicate edges and self-loops in place, preparing the graph for
deterministic serialization.

Algorithm:

1. For each adjacency list, replace it with the sorted set of its values.
2. Remove each source from its own adjacency list.

Requirements:

- **Idempotent** — safe to call multiple times.
- Resulting edge lists are sorted for stable dump.
- Sources with empty adjacency lists are **preserved** — a path without
  dependencies remains a graph node.

#### `remove_paths(paths: list[str])`

Deterministic pruning — drops endpoints from the graph in place. Used by
`run_update` for the endpoints of removed spec files.

- `paths`: API path templates (output of `extract_paths`, not file paths).

Algorithm:

1. Drop every entry present as an adjacency key.
2. Remove every entry from all remaining adjacency lists.

Requirements:

- Absent endpoints are ignored silently.
- Surviving keys and adjacency lists keep their relative order — serialized
  graphs stay diff-stable.
- Removal only — introduces no endpoints or edges; persistence stays with the
  caller (`deduplicate`, then save).

## Persistence

### `load_traceability(path: pathlib.Path) -> graph: TraceabilityGraph`

Reads `.swax/traceability.yml` into a `TraceabilityGraph`.

- `path`: path to the traceability file.
- `graph`: the loaded graph model.

Algorithm:

1. Read the file as UTF-8 text.
2. Parse YAML with the safe loader.
3. Normalize each adjacency value to a list.
4. Construct the graph from the normalized mapping.

Requirements:

- File is read as UTF-8.
- Parsing uses a **safe** YAML loader.
- An **empty file yields an empty graph**, not an error.

### `save_traceability(graph: TraceabilityGraph, path: pathlib.Path)`

Persists `TraceabilityGraph` to `.swax/traceability.yml` deterministically.

- `graph`: graph to write. Caller must have invoked `deduplicate` first.
- `path`: destination file path.

Algorithm:

1. Convert the model into YAML-safe primitives.
2. Create parent directories as needed.
3. Sort the edges mapping by key, and each adjacency list by value,
   **explicitly in Python**.
4. Dump YAML in a stable form and write as UTF-8.

Requirements:

- Parent directories are created as needed.
- Output is **stable across runs** — deterministic order of keys and values.
- Sorting is done in Python, **not** deferred to the YAML serializer.

## Traversal

### `find_affected_endpoints(changed_paths: list[str], graph: TraceabilityGraph) -> affected: list[str]`

Finds all endpoints transitively affected by a set of changed endpoints via the
traceability graph.

- `changed_paths`: endpoints that changed directly (the directly-changed set
  supplied by the caller).
- `graph`: the loaded traceability graph.
- `affected`: the changed endpoints plus every endpoint that transitively
  depends on them, sorted and deduplicated.

Algorithm:

1. Treat graph edges as `source → targets-it-depends-on` (`source` depends on
   `target`); a node's **dependents** are the nodes whose adjacency list
   contains it.
2. For each changed path, collect it and every node that transitively reaches
   it (reverse reachability).
3. Merge, deduplicate, sort.

Requirements:

- Returns the **complete** affected set — no internal cap.
- Changed paths not present as graph nodes are still returned.

Constraints:

- **Read-only** — does not mutate the graph.
- Does **not** import from the `openapi` cell; accepts plain path strings so
  the cell stays dependency-free.

## Errors

| Exception | Cause |
| --- | --- |
| `TraceabilityGraphMissingError(path: pathlib.Path)` | Raised when the traceability graph file does not exist — the project has not run `discover` yet. Carries the expected path to `.swax/traceability.yml`. |

## See also

- [Traceability graph](../../guide/traceability-graph.md) — file format and usage.
- [Architecture / applications/discover cell](applications.md#swaxapplicationsdiscover) —
  builds the graph.
- [Architecture / applications/plan cell](applications.md#swaxapplicationsplan) —
  consumes the graph.
- [Architecture / applications/update cell](applications.md#swaxapplicationsupdate) —
  prunes and revises the graph.
