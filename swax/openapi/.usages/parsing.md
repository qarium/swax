# Parsing — parsing OpenAPI/Swagger specifications

## Domain

Templates for discovering specification files and parsing them into a fully dereferenced dict. Target audience: cell `applications/discover/` (finds all specifications in a local directory and parses each one via Prance).

Prance expands `$ref` in memory, so subsequent code never has to resolve references manually. Swagger 2.0 and OpenAPI 3.x are handled transparently.

---

## Discovering specifications

`discover_specs` scans the directory by extension and a lightweight heuristic (the file must contain the `openapi` or `swagger` key near the start):

```python
from pathlib import Path

from swax.openapi import discover_specs


def collect_spec_files(specs_root: Path) -> list[Path]:
    return discover_specs(specs_root)
```

Consumer conventions:
- `root` — the local path from `SpecsConfig.location`.
- The heuristic is cheap (reads only the file head) — full parsing happens later via `parse_spec`.
- Returns a sorted list for deterministic processing order.

---

## Parsing a specification

`parse_spec` returns a fully dereferenced dict — `$ref` are already inlined:

```python
from pathlib import Path

from swax.openapi import parse_spec


def load_one_spec(spec_path: Path) -> dict:
    return parse_spec(spec_path)
```

Consumer conventions:
- Accepts `.yaml`, `.yml`, `.json` files.
- Returns a dict with `paths` and schemas (in `components.schemas` for OpenAPI 3.x or `definitions` for Swagger 2.0).
- On a parse error it raises `SpecParseError` with the file path and reason — the CLI handler maps it to `click.ClickException`.

---

## Composition: scan -> parse

A typical scenario in the use case:

```python
from swax.openapi import discover_specs, parse_spec


def load_all_specs(specs_root: Path) -> list[dict]:
    return [parse_spec(p) for p in discover_specs(specs_root)]
```

RAM constraint: Prance expands `$ref` in memory, so for very large specifications the RAM footprint may be significant — a known limitation, accepted by design.

---

## Recursive schemas

`parse_spec` supports self-referencing and mutually recursive schemas — a valid OpenAPI construct. Example:

```yaml
components:
  schemas:
    Polygon:
      type: object
      properties:
        children:
          type: array
          items:
            $ref: "#/components/schemas/Polygon"   # cycle
```

Behavior:

- All **non-cyclic** `$ref` are expanded in memory as usual.
- The cycle is expanded once (recursion limit = 1), then at the point of re-entry the marker `{"$ref": "#/components/schemas/Polygon"}` is substituted instead of infinite nesting.

```python
spec = parse_spec(path)
polygon = spec["components"]["schemas"]["Polygon"]
# The first level of children is expanded (all Polygon properties are visible),
# the cycle point is one level deeper.
children_items = polygon["properties"]["children"]["items"]
assert children_items["properties"]["children"]["items"] == {"$ref": "#/components/schemas/Polygon"}
```

Consumer conventions:

- Downstream code (extract_paths, extract_schemas, LLM context) must tolerate a `$ref` marker inside schema values — this is the expected cycle signal, not an unresolved reference.
- Post-resolve OpenAPI validation is intentionally disabled: it would reject valid recursive schemas after expansion. The `parse_spec` contract is about dict structure, not conformance to the OpenAPI schema.
