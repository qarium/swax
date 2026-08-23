---
title: Traceability graph
description: In-memory model and YAML persistence of API path dependencies — paths only, deterministic serialization.
---

# Traceability graph

The traceability graph is the central artifact produced by `swax discover`,
pruned and incrementally revised by `swax update`, and consumed by
`swax plan`. It models **API path → list of dependent paths**.

## Architectural rule

The graph stores **paths only** — no HTTP methods, no resource abstraction.
This is an architectural rule of Swax: **minimal abstraction**.

- **Nodes** = API paths (e.g. `/users`, `/users/{id}`).
- **Edges** = discovered dependencies between paths
  (`source` depends on `target`).

## File format

`.swax/traceability.yml`:

```yaml
/payment:
  - /users
  - /orders
/orders:
  - /payment
/users/{id}: []      # endpoint with no dependencies — still a node
```

- **Keys** are paths.
- **Values** are lists of dependent paths.
- An **endpoint with no dependencies** is still a node — every endpoint
  discovered in the parsed specs appears in the graph with at least an empty
  adjacency list.

## Determinism

`save_traceability` writes deterministic YAML:

- Parent directories are created as needed.
- Keys and values are **explicitly sorted in Python** — not deferred to the
  YAML serializer.
- Output is stable across runs for clean diffs.

`deduplicate` runs before saving:

- Removes duplicate edges.
- Removes self-loops.
- Sorts each adjacency list.
- **Preserves** sources with empty adjacency lists — paths with no
  dependencies remain graph nodes.

## Building the graph

`TraceabilityGraph` accumulates edges via `add_edge`:

```python
from swax.traceability import TraceabilityGraph

graph = TraceabilityGraph(edges={})
graph.add_edge(source="/payment", target="/users")
graph.add_edge(source="/payment", target="/orders")   # duplicates tolerated
graph.add_edge(source="/orders", target="/payment")
graph.deduplicate()
```

- Duplicates at insertion time are acceptable — they are removed by
  `deduplicate`.
- Self-loops are permitted at insert time and filtered by `deduplicate`.
- `deduplicate` is **idempotent** — safe to call multiple times.

## Pruning the graph

`TraceabilityGraph.remove_paths` drops endpoints deterministically — used by
`swax update` when spec files are removed from the remote repository:

```python
graph = TraceabilityGraph(edges={"/users": ["/legacy"], "/legacy": ["/users"]})
graph.remove_paths(["/legacy"])
graph.deduplicate()
# edges == {"/users": []}
```

- Drops every entry present as an adjacency **key**.
- Removes the entries from every **surviving adjacency list** (dangling
  references would corrupt `swax plan` results).
- **Preserves** the relative order of surviving keys and lists — serialized
  graphs stay diff-stable.
- Absent endpoints are ignored silently; removal only — no new endpoints or
  edges are introduced.
- Persistence stays with the caller: `deduplicate`, then save.

## Loading the graph

```python
from pathlib import Path
from swax.traceability import load_traceability

graph = load_traceability(Path(".swax/traceability.yml"))
```

- File is read as UTF-8.
- Parsing uses a **safe** YAML loader.
- An **empty file yields an empty graph**, not an error.
- Each adjacency value is normalized to a list.

## Finding affected endpoints

`find_affected_endpoints(changed_paths, graph)` returns every endpoint
transitively affected by a set of changed paths — the changed paths plus every
endpoint whose dependency chain reaches one of them (reverse reachability).

- Result is **sorted and deduplicated**.
- Changed paths not present as graph nodes are still returned.
- The routine is **read-only** — does not mutate the graph.
- Accepts plain path strings — does **not** depend on the `openapi` cell.

```python
from swax.traceability import find_affected_endpoints

affected = find_affected_endpoints(
    changed_paths=["/users", "/users/{id}"],
    graph=graph,
)
# ['/orders', '/payment', '/users', '/users/{id}']
```

## Errors

| Exception | Cause |
| --- | --- |
| `TraceabilityGraphMissingError(path)` | The graph file does not exist — `swax discover` has not been run yet. Raised by `run_plan`. |

## See also

- [Impact Report](impact-report.md) — how the graph feeds the plan command.
- [Architecture / traceability cell](../architecture/cells/traceability.md) —
  full API reference.
