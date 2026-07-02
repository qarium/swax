"""Logic tests for the swax.openapi cell.

Tests cover the four routines end-to-end: Prance-backed dereferencing (with the
$ref-resolution guarantee), the two extraction routines for both spec versions,
the discovery heuristic, and the SpecParseError wrapping on malformed input.
"""

import pathlib

import pytest
from swax.openapi import (
    SpecParseError,
    discover_specs,
    extract_paths,
    extract_schemas,
    parse_spec,
)


def _write(path: pathlib.Path, content: str) -> pathlib.Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestParseSpec:
    def test_parse_spec_returns_dereferenced_dict(self, tmp_path):
        spec_path = _write(
            tmp_path / "spec.yaml",
            """
openapi: 3.0.0
info:
  title: T
  version: "1.0"
paths:
  /users:
    get:
      responses:
        "200":
          description: ok
components:
  schemas:
    Order:
      type: object
      properties:
        id:
          type: integer
    User:
      type: object
      properties:
        orders:
          type: array
          items:
            $ref: "#/components/schemas/Order"
""".strip()
            + "\n",
        )

        spec = parse_spec(spec_path)

        items = spec["components"]["schemas"]["User"]["properties"]["orders"]["items"]
        assert isinstance(items, dict)
        assert "$ref" not in items
        assert items["type"] == "object"
        assert "properties" in items  # Order schema inlined by Prance

    def test_parse_spec_raises_on_invalid_yaml(self, tmp_path):
        spec_path = _write(tmp_path / "bad.yaml", ": not valid yaml: :")

        with pytest.raises(SpecParseError) as exc_info:
            parse_spec(spec_path)

        assert exc_info.value.path == spec_path
        assert isinstance(exc_info.value.reason, str)
        assert exc_info.value.reason  # non-empty reason surfaced from Prance


class TestExtractPaths:
    def test_extract_paths_returns_sorted_paths(self):
        spec = {"paths": {"/b": {}, "/a": {}}}

        assert extract_paths(spec) == ["/a", "/b"]

    def test_extract_paths_empty_when_no_paths(self):
        assert extract_paths({}) == []
        assert extract_paths({"paths": {}}) == []


class TestExtractSchemas:
    def test_extract_schemas_returns_components_schemas_for_openapi_3(self):
        spec = {
            "openapi": "3.0.0",
            "components": {"schemas": {"User": {"type": "object"}}},
        }

        schemas = extract_schemas(spec)

        assert set(schemas.keys()) == {"User"}

    def test_extract_schemas_returns_definitions_for_swagger_2(self):
        spec = {
            "swagger": "2.0",
            "definitions": {
                "User": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Order": {"type": "object", "properties": {}},
            },
        }

        schemas = extract_schemas(spec)

        assert set(schemas.keys()) == {"User", "Order"}
        assert schemas["User"]["type"] == "object"


class TestDiscoverSpecs:
    def test_discover_specs_filters_by_extension_and_head(self, tmp_path):
        _write(tmp_path / "api.yaml", "openapi: 3.0.0\npaths: {}\n")
        _write(tmp_path / "readme.md", "# readme\n")
        _write(tmp_path / "data.json", "{}")

        result = discover_specs(tmp_path)

        assert [path.name for path in result] == ["api.yaml"]

    def test_discover_specs_returns_sorted(self, tmp_path):
        _write(tmp_path / "beta.yaml", "openapi: 3.0.0\npaths: {}\n")
        _write(tmp_path / "alpha.yaml", "swagger: '2.0'\npaths: {}\n")

        result = discover_specs(tmp_path)

        assert [path.name for path in result] == ["alpha.yaml", "beta.yaml"]

    def test_discover_specs_detects_pretty_printed_json_spec(self, tmp_path):
        # A standard pretty-printed JSON spec puts '{' alone on line 1; a
        # single-line head read cannot locate the key and crashes the loader.
        # The whole-file cheap parse must still find it.
        _write(
            tmp_path / "api.json",
            '{\n  "openapi": "3.0.0",\n  "paths": {}\n}\n',
        )

        result = discover_specs(tmp_path)

        assert [path.name for path in result] == ["api.json"]

    def test_discover_specs_skips_unparseable_file_without_raising(self, tmp_path):
        # A .yaml/.json file whose content is not valid YAML/JSON must be
        # skipped, not crash the whole discovery run.
        _write(tmp_path / "broken.json", "{ not closed")
        _write(tmp_path / "api.yaml", "openapi: 3.0.0\npaths: {}\n")

        result = discover_specs(tmp_path)

        assert [path.name for path in result] == ["api.yaml"]

    def test_discover_specs_skips_non_utf8_binary_file_without_raising(self, tmp_path):
        # A binary or non-UTF-8 .json file (e.g. a stray UTF-16 BOM or random
        # bytes) makes read_text(encoding="utf-8") raise UnicodeDecodeError,
        # which is not a yaml.YAMLError and must not abort the whole run.
        (tmp_path / "binary.json").write_bytes(b"\xff\xfe\x00\x01garbage\xab")
        _write(tmp_path / "api.yaml", "openapi: 3.0.0\npaths: {}\n")

        result = discover_specs(tmp_path)

        assert [path.name for path in result] == ["api.yaml"]
