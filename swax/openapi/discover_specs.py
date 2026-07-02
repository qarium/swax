"""Discovery of specification files under a directory.

discover_specs walks a directory recursively and keeps files that both have a
spec extension (.yaml/.yml/.json) and whose content parses (via the cheap PyYAML
loader, which is a JSON superset) to a mapping carrying an ``openapi`` or
``swagger`` key. This is a lightweight content heuristic — full dereferencing is
deferred to parse_spec. A pretty-printed JSON spec puts ``{`` alone on its first
line, so a single-line read cannot locate the key and would crash the loader;
the whole-file cheap parse locates it for both YAML and JSON.
"""

import pathlib

import yaml

SPEC_EXTENSIONS: tuple[str, ...] = (".yaml", ".yml", ".json")


def discover_specs(root: pathlib.Path) -> list[pathlib.Path]:
    """Return the sorted spec file paths under root.

    Args:
        root: directory to search recursively.

    Returns:
        Sorted list of spec file paths (matched by extension and a top-level
        openapi/swagger key). Files that are not a parseable mapping with such
        a key are skipped; genuine parse failures for real specs surface later
        from parse_spec on the discovered candidates.
    """
    result: list[pathlib.Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SPEC_EXTENSIONS:
            continue
        try:
            head = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            # Not a cleanly readable/parseable candidate — skip. A binary or
            # non-UTF-8 file (UnicodeDecodeError), a file that vanishes mid-scan
            # (OSError), or malformed YAML/JSON (yaml.YAMLError) must not abort
            # the whole discovery run. Real spec parse errors are reported by
            # parse_spec, not by this cheap filter.
            continue
        if isinstance(head, dict) and ("openapi" in head or "swagger" in head):
            result.append(path)
    return sorted(result)


__all__: list[str] = [
    "discover_specs",
]
