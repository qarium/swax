"""Read-only access to OpenAPI/Swagger specifications.

The facade re-exports the four parsing/extraction routines and the
SpecParseError domain error. Swagger 2.0 and OpenAPI 3.x are handled
transparently — both store paths under paths. Schemas come from
components.schemas (3.x) or definitions (2.0). The traceability graph operates
on paths only.
"""

from .discover_specs import discover_specs
from .endpoint_diff import EndpointDiff
from .errors import SpecParseError
from .extract_paths import extract_paths
from .extract_schemas import extract_schemas
from .parse_spec import parse_spec

__all__: list[str] = [
    "EndpointDiff",
    "SpecParseError",
    "discover_specs",
    "extract_paths",
    "extract_schemas",
    "parse_spec",
]
