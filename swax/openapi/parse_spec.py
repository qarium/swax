"""Parsing of a single OpenAPI/Swagger specification into a dereferenced dict.

parse_spec hands the file to Prance's ResolvingParser, which inlines every $ref
in memory so the rest of Swax never resolves references manually. Any parser
failure is wrapped in SpecParseError with the offending path and the original
Prance reason, so the CLI handler can surface a readable message.
"""

import pathlib

from prance import ResolvingParser
from prance.util.resolver import RESOLVE_ALL

from .errors import SpecParseError


def parse_spec(spec_path: pathlib.Path) -> dict:
    """Parse and fully dereference a specification file.

    Args:
        spec_path: path to a .yaml/.yml/.json specification file.

    Returns:
        Fully dereferenced specification dict (all $ref inlined).

    Raises:
        SpecParseError: if Prance fails to parse or dereference the file.
    """
    try:
        parser = ResolvingParser(
            str(spec_path),
            backend="openapi-spec-validator",
            strict=False,
            # RESOLVE_ALL inlines internal JSON-pointer $ref (and external refs)
            # so downstream code never resolves references manually. A bare
            # resolve_types=True only enables HTTP refs and leaves internal
            # pointers unresolved, which would violate the dereference contract.
            resolve_types=RESOLVE_ALL,
        )
        return parser.specification
    except Exception as exc:  # Prance surfaces many error types; wrap uniformly.
        raise SpecParseError(path=spec_path, reason=str(exc)) from exc


__all__: list[str] = [
    "parse_spec",
]
