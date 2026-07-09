"""Parsing of a single OpenAPI/Swagger specification into a dereferenced dict.

parse_spec reads the file, parses YAML/JSON via Prance's formats helper, and
hands the parsed spec to Prance's RefResolver — the same resolver that
ResolvingParser uses internally — with a non-raising recursion_limit_handler.
The handler emits a ``{"$ref": ...}`` marker at cycle points so self-referential
schemas (e.g. Polygon -> Polygon) terminate cleanly instead of raising. Any
parser failure is wrapped in SpecParseError with the offending path and the
original Prance reason, so the CLI handler can surface a readable message.
"""

import pathlib

from prance.util.formats import parse_spec as _parse_spec_string
from prance.util.resolver import RESOLVE_ALL, RefResolver
from prance.util.url import absurl

from .errors import SpecParseError


def _handle_recursion(limit: int, parsed_url, recursions: tuple = ()) -> dict:  # noqa: ARG001
    """Stop inlining at a reference cycle by emitting a ``$ref`` marker.

    Returning a marker (instead of raising the default ResolutionError) lets
    self-referential and mutually-recursive schemas dereference to a finite
    structure: the cycle point retains a recognizable ``$ref`` while every
    non-cyclic reference is fully inlined.

    Args:
        limit: recursion limit configured on the resolver (unused — the
            handler always emits the marker).
        parsed_url: parsed URL of the reference that closed the cycle.
        recursions: stack of reference paths that led to the cycle (unused).

    Returns:
        ``{"$ref": "#<fragment>"}`` when the reference is internal, otherwise
        the full URL form ``{"$ref": "<absolute-url>"}``.
    """
    fragment = parsed_url.fragment
    if fragment:
        return {"$ref": f"#{fragment}"}
    return {"$ref": parsed_url.geturl()}


def parse_spec(spec_path: pathlib.Path) -> dict:
    """Parse and fully dereference a specification file.

    Args:
        spec_path: path to a .yaml/.yml/.json specification file.

    Returns:
        Fully dereferenced specification dict (all non-cyclic $ref inlined;
        cyclic $ref left as a marker at the cycle point).

    Raises:
        SpecParseError: if Prance fails to parse or dereference the file.
    """
    try:
        resolved_path = spec_path.resolve()
        spec_string = resolved_path.read_text(encoding="utf-8")
        parsed = _parse_spec_string(spec_string, filename=str(resolved_path))

        resolver = RefResolver(
            parsed,
            absurl(resolved_path.as_uri(), None),
            strict=False,
            resolve_types=RESOLVE_ALL,
            recursion_limit_handler=_handle_recursion,
        )
        resolver.resolve_references()
        return resolver.specs
    except Exception as exc:  # Prance surfaces many error types; wrap uniformly.
        raise SpecParseError(path=spec_path, reason=str(exc)) from exc


__all__: list[str] = [
    "parse_spec",
]
