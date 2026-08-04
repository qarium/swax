# Affected endpoints — graph-based impact mapping

## Domain

How to compute the endpoints transitively affected by a set of changed paths. Target audience:
cell `applications/plan/` (`run_plan`).

The graph stores source -> its dependencies. A changed endpoint affects itself plus everyone who
(transitively) depends on it (reverse reachability: every node that reaches the changed node via
depends-on edges).

## Mapping changes to affected endpoints

```python
from swax.traceability import find_affected_endpoints, load_traceability

graph = load_traceability(traceability_path)
affected = find_affected_endpoints(changed_paths=changes.changed_paths(), graph=graph)
```

`affected` is a sorted, deduplicated `list[str]` covering the full transitive closure.

## Preconditions

The graph must exist — a missing file should surface as `TraceabilityGraphMissingError`
(raised by `run_plan`). The routine is read-only and accepts plain path strings.
