# PyYAML — YAML I/O

## Domain

Patterns for reading and writing YAML files used by Swax: `.swax/config.yml` and `.swax/traceability.yml`. Target audience: cells that persist configuration or the traceability graph.

Swax stores state exclusively in YAML files — no databases, no vector storage (architecture rule).

---

## Loading

Always use `yaml.safe_load` to avoid arbitrary code execution. Read text explicitly with `pathlib.Path.read_text` for encoding control.

```python
import pathlib

import yaml


def load_config(path: pathlib.Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config.model_validate(raw)
```

For the traceability graph (a flat mapping of paths to dependency lists):

```python
def load_traceability(path: pathlib.Path) -> dict[str, list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {k: list(v) for k, v in (data or {}).items()}
```

---

## Dumping

Use `yaml.safe_dump` with deterministic options so diffs stay reviewable:

```python
def save_config(config: Config, path: pathlib.Path) -> None:
    payload = config.model_dump(mode="json")
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
```

For the traceability graph:

```python
def save_traceability(graph: dict[str, list[str]], path: pathlib.Path) -> None:
    ordered = {k: sorted(graph[k]) for k in sorted(graph)}
    path.write_text(
        yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
```

Sort keys explicitly in Python rather than relying on `sort_keys=True` — this gives control over nested structures.

---

## Pydantic Interop

Dump pydantic models with `mode="json"` to ensure enums and dates serialize to YAML-compatible primitives.

```python
payload = model.model_dump(mode="json")
yaml.safe_dump(payload, ...)
```

---

## File Creation Discipline

Always create parent directories before writing:

```python
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(...)
```