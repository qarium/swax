"""Discovery of specification files under a directory.

discover_specs walks a directory recursively and keeps files that both have a
spec extension (.yaml/.yml/.json) and whose first line carries an openapi or
swagger key. This is a cheap head-only heuristic — full parsing and
dereferencing are deferred to parse_spec.
"""

import pathlib

import yaml

SPEC_EXTENSIONS: tuple[str, ...] = (".yaml", ".yml", ".json")


def discover_specs(root: pathlib.Path) -> list[pathlib.Path]:
    """Return the sorted spec file paths under root.

    Args:
        root: directory to search recursively.

    Returns:
        Sorted list of spec file paths (matched by extension and head key).
    """
    result: list[pathlib.Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SPEC_EXTENSIONS:
            continue
        with path.open(encoding="utf-8") as handle:
            head_text = handle.readline() or "{}"
        head = yaml.safe_load(head_text)
        if isinstance(head, dict) and ("openapi" in head or "swagger" in head):
            result.append(path)
    return sorted(result)


__all__: list[str] = [
    "discover_specs",
]
