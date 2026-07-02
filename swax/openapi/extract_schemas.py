"""Extraction of schema definitions from a parsed specification.

extract_schemas transparently distinguishes OpenAPI 3.x (components.schemas)
from Swagger 2.0 (definitions) and returns the schema mapping. Schemas are used
only by the LLM refine prompt — they are never stored in the traceability
graph, which holds paths only.
"""


def extract_schemas(spec: dict) -> dict:
    """Return schema definitions from a parsed specification.

    OpenAPI 3.x stores schemas under components.schemas; Swagger 2.0 stores
    them under definitions.

    Args:
        spec: dereferenced specification dict (output of parse_spec).

    Returns:
        Mapping of schema name to its (already inlined) definition.
    """
    if "components" in spec:
        return spec["components"].get("schemas", {})
    return spec.get("definitions", {})


__all__: list[str] = [
    "extract_schemas",
]
