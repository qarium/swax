# Incremental graph prompts — revising an existing traceability graph

## Domain

Prompt templates for the incremental traceability graph rebuild. Target audience: cell
`applications/update/` (assembles the LLM input when specs changed and a graph already exists).

The scenario is single-turn: the model receives the current graph plus endpoint-level changes
and returns the complete updated dependency mapping.

---

## Assembling the prompt pair

```python
from swax.prompts import (
    build_incremental_graph_system_prompt,
    build_incremental_graph_user_prompt,
)

system = build_incremental_graph_system_prompt()
user = build_incremental_graph_user_prompt(
    existing_edges=graph.edges,
    diff_added=diff.added,
    diff_removed=diff.removed,
    diff_modified=diff.modified,
    added_endpoints=added_endpoints,
    added_schemas=added_schemas,
)
response = client.ask(system=system, user=user)
```

Consumer conventions:
- `existing_edges` comes straight from the loaded `TraceabilityGraph` — no preprocessing.
- `diff_*` mirror the `EndpointDiff` shape: two sorted path lists and a path -> descriptions
  mapping.
- `added_*` come from `extract_paths` / `extract_schemas` over the newly added spec files.
- Merge the endpoint-level changes of all modified files into one diff set before calling.

## Output contract

The model returns one JSON object: source path -> list of dependent paths, covering the full
updated graph (not a delta). Parse defensively — strip prose/code fences, validate the shape
`dict[str, list[str]]`, and drop sources/targets outside the endpoint universe.

## Testing

Builders are pure string functions — assert on stable fragments (role, JSON contract,
universe rule) rather than full prompt equality.
