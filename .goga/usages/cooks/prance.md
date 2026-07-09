# Prance — OpenAPI/Swagger Parsing

## Domain

Patterns for parsing and dereferencing OpenAPI 3.x and Swagger 2.0 specifications. Target audience: the `domain/openapi/` cell. Prance resolves `$ref` references to produce a fully-dereferenced spec the rest of Swax can consume.

Swax extracts only API paths from specs — no HTTP method abstraction, no resource abstraction (architecture rule: minimal abstraction).

---

## Dereferenced Parsing

Drive Prance's `RefResolver` directly (instead of `ResolvingParser`) to fully
inline `$ref` without triggering Prance's post-resolve `openapi-spec-validator`
step — that validator rejects valid recursive schemas after they are
dereferenced. A non-raising `recursion_limit_handler` terminates reference
cycles by emitting a `{"$ref": ...}` marker, so self-referential and
mutually-recursive schemas parse cleanly.

```python
import pathlib

from prance.util.formats import parse_spec as parse_spec_string
from prance.util.resolver import RESOLVE_ALL, RefResolver
from prance.util.url import absurl


def _handle_recursion(limit, parsed_url, recursions=()):
    fragment = parsed_url.fragment
    return {"$ref": f"#{fragment}"} if fragment else {"$ref": parsed_url.geturl()}


def parse_spec(spec_path: pathlib.Path) -> dict:
    resolved = spec_path.resolve()
    parsed = parse_spec_string(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    resolver = RefResolver(
        parsed,
        absurl(resolved.as_uri(), None),
        strict=False,
        resolve_types=RESOLVE_ALL,
        recursion_limit_handler=_handle_recursion,
    )
    resolver.resolve_references()
    return resolver.specs
```

The resolved dict contains:
- `paths` — mapping of path templates to method definitions
- `components` / `definitions` — schemas (already inlined into their references)
- At reference cycles: a `{"$ref": ...}` marker instead of infinite nesting

Why not `ResolvingParser` directly: its built-in post-resolve validator
(`openapi-spec-validator`) raises on the dereferenced form of recursive
schemas (the cycle-terminated branch fails `oneOf(Schema | Reference)`).
Driving `RefResolver` ourselves keeps dereferencing semantics identical for
non-recursive specs while bypassing that validator.

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