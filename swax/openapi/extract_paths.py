"""Extraction of API path templates from a parsed specification.

extract_paths returns the sorted path keys of a dereferenced spec, discarding
HTTP methods — the traceability graph operates on paths only (no method-level
nodes), per the architectural rule of minimal abstraction.
"""


def extract_paths(spec: dict) -> list[str]:
    """Return the sorted API path templates from a parsed specification.

    Args:
        spec: dereferenced specification dict (output of parse_spec).

    Returns:
        Sorted list of path templates (e.g. /users, /users/{id}).
    """
    return sorted(spec.get("paths", {}).keys())


__all__: list[str] = [
    "extract_paths",
]
