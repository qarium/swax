"""Contract tests for the swax.openapi cell.

These tests pin the public surface and signatures of the four routines and the
SpecParseError entity. They fail with ImportError until the modules and the
facade re-exports exist (task 9).
"""

import inspect
import pathlib

import pytest
from swax.openapi import (
    SpecParseError,
    discover_specs,
    extract_paths,
    extract_schemas,
    parse_spec,
)


class TestOpenApiContract:
    def test_entities_are_importable_from_facade(self):
        assert callable(parse_spec)
        assert callable(extract_paths)
        assert callable(extract_schemas)
        assert callable(discover_specs)
        assert issubclass(SpecParseError, Exception)

    def test_parse_spec_signature(self):
        signature = inspect.signature(parse_spec)

        assert list(signature.parameters) == ["spec_path"]
        assert signature.parameters["spec_path"].annotation is pathlib.Path
        assert signature.return_annotation is dict

    def test_extract_paths_signature(self):
        signature = inspect.signature(extract_paths)

        assert list(signature.parameters) == ["spec"]
        assert signature.parameters["spec"].annotation is dict
        assert signature.return_annotation == list[str]

    def test_extract_schemas_signature(self):
        signature = inspect.signature(extract_schemas)

        assert list(signature.parameters) == ["spec"]
        assert signature.parameters["spec"].annotation is dict
        assert signature.return_annotation is dict

    def test_discover_specs_signature(self):
        signature = inspect.signature(discover_specs)

        assert list(signature.parameters) == ["root"]
        assert signature.parameters["root"].annotation is pathlib.Path
        assert signature.return_annotation == list[pathlib.Path]

    def test_spec_parse_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            SpecParseError(pathlib.Path("/x"), "boom")
