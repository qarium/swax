# Structural diff — comparing two dereferenced specs

## Domain

Patterns for computing and classifying a structural diff between a baseline and a fresh
specification. Target audience: cell `applications/plan/` (`run_plan` consumes `diff_specs`,
`classify_endpoint_changes`, and `EndpointDiff`).

Diff operates on fully dereferenced specs — Prance already inlined `$ref` during parsing.
The traceability graph stores paths only; diff granularity is for analysis.

## Computing a diff

```python
from swax.openapi import diff_specs, classify_endpoint_changes

raw = diff_specs(base_spec, current_spec)
changes = classify_endpoint_changes(raw)
```

`diff_specs` returns a `DeepDiff`; `classify_endpoint_changes` turns it into an `EndpointDiff`.

## Reading EndpointDiff

- `changes.added` / `changes.removed` — `list[str]` of endpoint paths.
- `changes.modified` — `dict[str, list[str]]`: path -> change descriptions.
- `changes.has_changes()` — skip the LLM when nothing changed.
- `changes.changed_paths()` — the endpoint set to map onto the graph.

## Preconditions

Both specs must come from `parse_spec` (dereferenced). Schema changes under
`components`/`definitions` are attributed to the endpoints that reference them automatically.
