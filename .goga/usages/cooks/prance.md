# Prance — OpenAPI/Swagger Parsing

## Domain

Patterns for parsing and dereferencing OpenAPI 3.x and Swagger 2.0 specifications. Target audience: the `domain/openapi/` cell. Prance resolves `$ref` references to produce a fully-dereferenced spec the rest of Swax can consume.

Swax extracts only API paths from specs — no HTTP method abstraction, no resource abstraction (architecture rule: minimal abstraction).

---

## Dereferenced Parsing

Use `prance.ApiResolver` (or `ResolvingParser`) to inline `$ref` so downstream code never resolves references manually.

```python
import pathlib

from prance import ResolvingParser


def parse_spec(spec_path: pathlib.Path) -> dict:
    parser = ResolvingParser(
        str(spec_path),
        backend="openapi-spec-validator",
        strict=False,
        resolve_types=True,
    )
    return parser.specification
```

The resolved `specification` dict contains:
- `paths` — mapping of path templates to method definitions
- `components` / `definitions` — schemas (already inlined into their references)

---

## Extracting Paths

Iterate `specification["paths"]` to collect API path templates. Strip HTTP methods — the traceability graph operates on paths only.

```python
def extract_paths(spec: dict) -> list[str]:
    return sorted(spec.get("paths", {}).keys())
```

Result feeds directly into the traceability graph node set.

---

## Supporting Both Spec Versions

Prance handles Swagger 2.0 and OpenAPI 3.x transparently. Both store paths under `paths` — no version-specific code is required for path extraction.

If schema introspection is needed (for the LLM context-enrichment step):

```python
def extract_schemas(spec: dict) -> dict:
    # OpenAPI 3.x
    if "components" in spec:
        return spec["components"].get("schemas", {})
    # Swagger 2.0
    return spec.get("definitions", {})
```

---

## Error Handling

Wrap parser errors in a domain exception with the spec filename for diagnosis.

```python
from prance.util.fs import FileNotFoundError as PranceFileNotFoundError


def parse_or_raise(spec_path: pathlib.Path) -> dict:
    try:
        return parse_spec(spec_path)
    except (PranceFileNotFoundError, Exception) as exc:
        raise SpecParseError(path=spec_path, reason=str(exc)) from exc
```

---

## Multiple Spec Discovery

Discover spec files by extension when the repo location contains multiple specs.

```python
SPEC_EXTENSIONS = (".yaml", ".yml", ".json")


def discover_specs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.suffix.lower() in SPEC_EXTENSIONS and _looks_like_spec(p)
    )


def _looks_like_spec(path: pathlib.Path) -> bool:
    head = yaml.safe_load(path.read_text(encoding="utf-8").splitlines()[0] or "{}")
    return isinstance(head, dict) and ("openapi" in head or "swagger" in head)
```

Lightweight heuristic — full parse happens later via Prance.