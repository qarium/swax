# Extraction — paths and schemas from a parsed specification

## Domain

Templates for extracting data from a parsed specification to build the traceability graph. Target audience: cell `applications/discover/` (collects graph nodes from paths and prepares schemas for the refinement LLM pass).

The traceability graph operates on paths only — no HTTP methods, no resource abstraction. This is an architectural rule of Swax: minimal abstraction.

---

## Extracting paths (graph nodes)

`extract_paths` returns a sorted list of API paths from the parsed specification:

```python
from swax.openapi import extract_paths


def collect_nodes(spec: dict) -> list[str]:
    return extract_paths(spec)
```

Consumer conventions:
- `spec` — the output of `parse_spec` (a dereferenced dict).
- Returns path templates (e.g., `/users`, `/users/{id}`).
- The result directly becomes the nodes of the traceability graph — methods are not present in the graph.

---

## Extracting schemas (context for the LLM)

`extract_schemas` returns schema definitions for the refinement LLM pass. The function automatically distinguishes OpenAPI 3.x (`components.schemas`) from Swagger 2.0 (`definitions`):

```python
from swax.openapi import extract_schemas


def collect_schema_context(spec: dict) -> dict:
    return extract_schemas(spec)
```

Consumer conventions:
- Schemas are used ONLY in `build_refine_user_prompt` (cell `prompts/`) to refine ambiguous dependency pairs.
- Schemas are NEVER stored in the traceability graph — the graph stores only paths.

---

## Full extraction scenario

```python
from swax.openapi import extract_paths, extract_schemas


def extract_graph_input(spec: dict) -> tuple[list[str], dict]:
    return extract_paths(spec), extract_schemas(spec)
```

The `run_discover` use case aggregates paths from all specifications into a single list of nodes and passes schemas to the refinement prompt when needed.
