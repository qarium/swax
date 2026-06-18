# DeepDiff — Structural Diff of OpenAPI Specs

## Domain

Patterns for computing structural diffs between two OpenAPI/Swagger specifications using `deepdiff`. Target audience: the `domain/openapi/diff/` cell used by the `plan` command.

Diff operates on **fully dereferenced** specs (Prance already inlined `$ref` — see `prance.md`). After diffing, results are classified into Swax-relevant categories: added / modified / removed endpoints with optional schema-level detail.

The traceability graph still stores only paths — diff granularity is for analysis, not for the graph.

---

## Basic Diff

`DeepDiff` compares two dicts and returns a structured result with change categories:

```python
from deepdiff import DeepDiff


def diff_specs(base: dict, current: dict) -> DeepDiff:
    return DeepDiff(
        base,
        current,
        ignore_order=True,
        report_repetition=False,
        cutoff_intersection_for_pairs=1,
    )
```

`ignore_order=True` — list order does not matter for spec comparison.

---

## Accessing Changes

`DeepDiff` returns an object with named change sets:

```python
result = diff_specs(base_spec, current_spec)

result.keys_added         # new keys (e.g. new path, new schema field)
result.keys_removed       # removed keys
result.values_changed     # modified values
result.type_changes       # changed types
result.set_item_added     # new items in sets
result.set_item_removed   # removed items
```

Each entry references the path within the structure (e.g. `root['paths']['/users']['get']['responses']['200']`).

---

## Classifying by Spec Domain

Walk DeepDiff paths to classify changes into endpoint-level categories. Paths under `paths` are endpoint changes; paths under `components`/`definitions` are schema changes.

```python
def classify_endpoint_changes(diff_result: DeepDiff) -> EndpointDiff:
    added: list[str] = []
    removed: list[str] = []
    modified: dict[str, list[str]] = {}

    for key in diff_result.get("keys_added", []) or []:
        if (path := _extract_path_key(key)) and path.startswith("paths['"):
            added.append(_endpoint_from_path(path))

    for key in diff_result.get("keys_removed", []) or []:
        if (path := _extract_path_key(key)) and path.startswith("paths['"):
            removed.append(_endpoint_from_path(path))

    for key in (diff_result.get("values_changed", {}) or {}):
        if (path := _extract_path_key(key)) and path.startswith("paths['"):
            endpoint = _endpoint_from_path(path)
            modified.setdefault(endpoint, []).append(_change_at_path(key))

    return EndpointDiff(added=added, removed=removed, modified=modified)
```

Helpers extract endpoint and change detail from DeepDiff path strings.

---

## Mapping Schema Changes to Endpoints

When a schema under `components`/`definitions` changes, affected endpoints are those whose dereferenced payload referenced it. Since Prance already inlined `$ref`, the schema change appears as `values_changed` under each consumer endpoint directly — classification picks it up automatically.

---

## Performance and Size

For large specs, set `cutoff` to skip identical subtrees early:

```python
DeepDiff(base, current, cutoff_intersection_for_pairs=1, verbose_level=1)
```

Avoid `verbose_level=2` in production paths — it computes expensive metadata.

---

## Serialization

DeepDiff objects serialize to JSON for debugging. Use this only in DEBUG logs:

```python
import json

logger.debug("raw diff", extra={"diff": json.loads(diff_result.to_json())})
```

---

## Testing

`deepdiff.DeepDiff` is deterministic — assert on it directly.

```python
def test_diff_detects_added_endpoint() -> None:
    base = {"paths": {"/users": {}}}
    current = {"paths": {"/users": {}, "/orders": {}}}
    result = diff_specs(base, current)
    classified = classify_endpoint_changes(result)
    assert "/orders" in classified.added
```