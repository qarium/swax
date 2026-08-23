# Traceability graph — lifecycle and persistence

## Domain

Templates for building and persisting the API traceability graph. Target audience: cells `applications/discover/` (accumulates edges from the LLM output and saves the graph to `.swax/traceability.yml`) and `applications/update/` (loads, prunes, and re-saves the graph).

The graph operates on paths only — no HTTP methods, no resource abstraction. This is an architectural rule of Swax: minimal abstraction. Nodes = API paths, edges = discovered dependencies between endpoints.

The `.swax/traceability.yml` file format:
```yaml
/payment:
  - /users
  - /orders
/orders:
  - /payment
```
Keys are paths, values are lists of dependent paths.

---

## Building the graph

`TraceabilityGraph` accumulates edges via `add_edge` during the LLM analysis:

```python
from swax.traceability import TraceabilityGraph


def build_from_llm_output(dependencies: dict[str, list[str]]) -> TraceabilityGraph:
    graph = TraceabilityGraph(edges={})
    for source, targets in dependencies.items():
        for target in targets:
            graph.add_edge(source=source, target=target)
    return graph
```

Consumer conventions:
- `source` — the path that depends on another.
- `target` — the path that `source` depends on.
- Duplicates at insertion time are acceptable — they are removed later via `deduplicate`.

---

## Deduplication before saving

Before serialization the graph is always deduplicated — this removes duplicate edges and self-dependencies, ensuring deterministic output:

```python
from swax.traceability import TraceabilityGraph


def finalize(graph: TraceabilityGraph) -> TraceabilityGraph:
    graph.deduplicate()
    return graph
```

Consumer conventions:
- Idempotent — safe to call multiple times.
- Returns sorted edge lists within each key.
- Empty adjacency lists are preserved — a path without dependencies remains a graph node. `run_discover` relies on this, guaranteeing that every endpoint from the specifications is present in `.swax/traceability.yml`.

---

## Saving the graph

`save_traceability` writes deterministic YAML: keys and values are explicitly sorted in Python for a stable diff between runs:

```python
from pathlib import Path

from swax.traceability import TraceabilityGraph, save_traceability


def persist(graph: TraceabilityGraph, project_root: Path) -> None:
    save_traceability(graph, project_root / ".swax" / "traceability.yml")
```

Consumer conventions:
- Pass a graph that has already had `deduplicate` called.
- The function creates parent directories as needed.
- `mode="json"` for the pydantic dump guarantees YAML-compatible primitives.

---

## Reading the graph

`load_traceability` reads `.swax/traceability.yml` back into the model. An empty file yields an empty graph, not an error:

```python
from pathlib import Path

from swax.traceability import load_traceability


def reload(project_root: Path):
    return load_traceability(project_root / ".swax" / "traceability.yml")
```

Reading is used for subsequent graph analysis; the `discover` scenario only writes the graph, it does not read it.

---

## Pruning removed endpoints

When spec files disappear from the remote side, their endpoints leave the graph
deterministically — no LLM pass is needed. Extract the endpoint paths from the removed
files' last local content, then:

```python
from swax.traceability import TraceabilityGraph


def prune_removed(graph: TraceabilityGraph, removed_endpoints: list[str]) -> TraceabilityGraph:
    graph.remove_paths(paths=removed_endpoints)
    graph.deduplicate()
    return graph
```

Consumer conventions:
- `paths` are API path templates (output of `extract_paths` over the removed files) — not
  file paths.
- Endpoints of surviving files and edges between them are preserved untouched.
- Call `deduplicate` before persisting — the pruned graph follows the same save contract as
  a fresh one.
- Save the result atomically when the write must not damage the previous graph on failure.
