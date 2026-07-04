"""Logic tests for the swax.applications.discover cell (task 17).

build_llm_client is mocked at its import point
(swax.applications.discover.run_discover.build_llm_client) so no live LLM is
contacted; parse_spec runs for real against a local spec fixture (prance works
offline on a self-contained file). The scenarios cover the full two-pass happy
path (incl. the multi-turn message structure), the defensive first-pass parser
failure, uncertain-pair forwarding to the refine prompt, fresh-graph overwriting
of an existing traceability.yml, propagation of the five non-parse domain
errors, and direct unit coverage of the _parse_llm_json helper.
"""

import json
import pathlib

import pytest
import yaml
from swax.applications.discover import run_discover
from swax.applications.discover.run_discover import _merge_dependencies, _parse_llm_json
from swax.config import MissingEnvironmentVariablesError
from swax.llm import (
    LLMCallError,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
)
from swax.openapi import SpecParseError

BUILD_CLIENT = "swax.applications.discover.run_discover.build_llm_client"
PARSE_SPEC = "swax.applications.discover.run_discover.parse_spec"

ENV_VARS = {
    "SWAX_LLM_MODEL": "claude-test-model",
    "SWAX_LLM_PROTOCOL": "anthropic",
    "SWAX_LLM_BASE_URL": "https://example.com",
    "SWAX_LLM_TOKEN": "test-token",
}

CONFIG_YML = """\
git:
  url: https://example.com/repo.git
  location: specs/
specs:
  type: openapi
  location: specs
"""

OPENAPI_SPEC = """\
openapi: 3.0.0
info:
  title: Test
  version: 1.0.0
paths:
  /users:
    get:
      responses:
        '200':
          description: ok
  /users/{id}:
    get:
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: ok
"""


@pytest.fixture
def discover_project(tmp_path, monkeypatch):
    """Materialize a minimal project: .swax/config.yml + specs/api.yaml + env."""
    swax_dir = tmp_path / ".swax"
    swax_dir.mkdir()
    (swax_dir / "config.yml").write_text(CONFIG_YML, encoding="utf-8")
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "api.yaml").write_text(OPENAPI_SPEC, encoding="utf-8")
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    return tmp_path


def _trace_path(project_root: pathlib.Path) -> pathlib.Path:
    return project_root / ".swax" / "traceability.yml"


class TestRunDiscoverTwoPass:
    def test_run_discover_builds_graph_with_two_llm_passes(self, discover_project, mocker):
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"uncertain": [], "dependencies": {"/users": ["/users/{id}"]}}'
        # Refine pass returns a flat dict[str, list[str]] (first_pass=False).
        mock_client.ask_multi_turn.return_value = '{"/users": ["/users/{id}"]}'

        run_discover(project_root=discover_project)

        trace_path = _trace_path(discover_project)
        assert trace_path.exists()
        data = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
        # Both endpoints from the spec appear as nodes; /users/{id} has no
        # outgoing dependencies and is preserved with an empty adjacency list.
        assert data == {"/users": ["/users/{id}"], "/users/{id}": []}
        mock_client.ask.assert_called_once()
        mock_client.ask_multi_turn.assert_called_once()
        _, kwargs = mock_client.ask_multi_turn.call_args
        messages = kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_run_discover_raises_llm_response_parse_error_on_invalid_first_pass(self, discover_project, mocker):
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        # First-pass response is missing the "uncertain" key.
        mock_client.ask.return_value = 'Sorry, here is my answer: {"dependencies": {"/users": ["/orders"]}}'

        with pytest.raises(LLMResponseParseError) as exc_info:
            run_discover(project_root=discover_project)

        assert "dependencies+uncertain" in exc_info.value.reason
        mock_client.ask_multi_turn.assert_not_called()

    def test_run_discover_passes_uncertain_pairs_to_refine(self, discover_project, mocker):
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"dependencies": {"/users": ["/orders"]}, "uncertain": ["/users -> /orders"]}'
        mock_client.ask_multi_turn.return_value = '{"/users": ["/orders"]}'

        run_discover(project_root=discover_project)

        _, kwargs = mock_client.ask_multi_turn.call_args
        refine_message = kwargs["messages"][2]["content"]
        assert "/users -> /orders" in refine_message
        assert kwargs["messages"][1]["content"] == mock_client.ask.return_value
        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        # The spec only declares /users and /users/{id}; /orders is foreign and
        # is filtered out of both source and target lists. The resulting graph
        # keeps the spec endpoints as nodes (with empty adjacencies here).
        assert data == {"/users": [], "/users/{id}": []}

    def test_run_discover_overwrites_existing_traceability_yml(self, discover_project, mocker):
        existing = _trace_path(discover_project)
        existing.write_text("/old:\n- /path\n", encoding="utf-8")
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"uncertain": [], "dependencies": {"/users": ["/users/{id}"]}}'
        mock_client.ask_multi_turn.return_value = '{"/users": ["/users/{id}"]}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(existing.read_text(encoding="utf-8"))
        assert data == {"/users": ["/users/{id}"], "/users/{id}": []}
        assert "/old" not in data

    def test_run_discover_normalizes_wrapped_refine_response(self, discover_project, mocker):
        # The refine pass sometimes returns {"dependencies": {...}} (the model
        # drags the first-pass envelope into the multi-turn response despite the
        # prompt contract). run_discover must unwrap it and persist the graph.
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"uncertain": [], "dependencies": {"/users": ["/users/{id}"]}}'
        mock_client.ask_multi_turn.return_value = '{"dependencies": {"/users": ["/users/{id}"]}}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        assert data == {"/users": ["/users/{id}"], "/users/{id}": []}


class TestRunDiscoverErrorPropagation:
    @pytest.mark.parametrize(
        "error_id",
        [
            "missing_env",
            "spec_parse",
            "llm_call",
            "rate_limited",
            "unsupported_protocol",
        ],
    )
    def test_run_discover_propagates_domain_errors(self, discover_project, mocker, monkeypatch, error_id):
        expected = {
            "missing_env": MissingEnvironmentVariablesError,
            "spec_parse": SpecParseError,
            "llm_call": LLMCallError,
            "rate_limited": LLMRateLimitedError,
            "unsupported_protocol": UnsupportedLLMProtocolError,
        }[error_id]

        if error_id == "missing_env":
            for var in ENV_VARS:
                monkeypatch.delenv(var, raising=False)
        elif error_id == "spec_parse":
            mocker.patch(
                PARSE_SPEC,
                side_effect=SpecParseError(path=discover_project / "specs" / "api.yaml", reason="boom"),
            )
        else:
            mock_build = mocker.patch(BUILD_CLIENT)
            if error_id == "unsupported_protocol":
                mock_build.side_effect = UnsupportedLLMProtocolError(protocol="ftp")
            else:
                mock_client = mock_build.return_value
                mock_client.ask.side_effect = {
                    "llm_call": LLMCallError(reason="boom"),
                    "rate_limited": LLMRateLimitedError(reason="boom"),
                }[error_id]

        with pytest.raises(expected):
            run_discover(project_root=discover_project)


class TestRunDiscoverEndpointGuarantee:
    """Coverage for the bug where endpoints were dropped from the graph when the
    LLM omitted them. All endpoints from the parsed specs must appear as graph
    nodes; foreign paths introduced by the LLM must be filtered out; confident
    edges from the first pass must merge with refined pairs."""

    def test_run_discover_keeps_endpoint_with_no_dependencies(self, discover_project, mocker):
        # Neither LLM pass mentions /users/{id}. It must still appear as a node
        # with an empty adjacency list — this is the regression that motivated
        # the fix.
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"uncertain": [], "dependencies": {"/users": ["/users/{id}"]}}'
        mock_client.ask_multi_turn.return_value = '{"/users": ["/users/{id}"]}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        assert data == {"/users": ["/users/{id}"], "/users/{id}": []}

    def test_run_discover_merges_first_pass_with_refine(self, discover_project, mocker):
        # First pass confidently reports /a -> /b (here /users -> /users/{id});
        # refine resolves a separate uncertain pair. The final graph contains
        # edges from both passes plus all spec endpoints as nodes.
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"dependencies": {"/users": ["/users/{id}"]}, "uncertain": []}'
        mock_client.ask_multi_turn.return_value = '{"/users/{id}": ["/users"]}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        # First-pass edge /users -> /users/{id} survives; refine adds the
        # reverse edge /users/{id} -> /users; both endpoints are nodes.
        assert data == {"/users": ["/users/{id}"], "/users/{id}": ["/users"]}

    def test_run_discover_drops_paths_outside_endpoint_universe(self, discover_project, mocker):
        # The refine pass invents a foreign path /orders which is not in the
        # spec. It must not appear in the saved graph (neither as a source nor
        # as a target).
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = '{"uncertain": [], "dependencies": {}}'
        mock_client.ask_multi_turn.return_value = '{"/users": ["/orders"], "/orders": ["/users/{id}"]}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        assert "/orders" not in data
        assert all("/orders" not in targets for targets in data.values())
        # Spec endpoints are still present as nodes.
        assert set(data.keys()) == {"/users", "/users/{id}"}

    def test_run_discover_refine_empty_list_keeps_first_pass_edges(self, discover_project, mocker):
        # When the refine pass returns an empty list for a key that the first
        # pass populated with confident edges, the confident edges survive — an
        # empty refine answer is treated as "no new information", not as
        # "delete what the first pass said".
        mock_build = mocker.patch(BUILD_CLIENT)
        mock_client = mock_build.return_value
        mock_client.ask.return_value = (
            '{"dependencies": {"/users": ["/users/{id}"]}, "uncertain": ["/users -> /users/{id}"]}'
        )
        mock_client.ask_multi_turn.return_value = '{"/users": []}'

        run_discover(project_root=discover_project)

        data = yaml.safe_load(_trace_path(discover_project).read_text(encoding="utf-8"))
        assert data == {"/users": ["/users/{id}"], "/users/{id}": []}


class TestMergeDependenciesHelper:
    def test_merge_guarantees_all_endpoints_as_nodes(self):
        merged = _merge_dependencies(first={}, refined={}, allowed_nodes={"/a", "/b"})

        assert merged == {"/a": [], "/b": []}

    def test_merge_combines_first_and_refined_edges(self):
        merged = _merge_dependencies(
            first={"/a": ["/b"]},
            refined={"/b": ["/a"]},
            allowed_nodes={"/a", "/b"},
        )

        assert merged == {"/a": ["/b"], "/b": ["/a"]}

    def test_merge_refine_overrides_first_with_non_empty(self):
        merged = _merge_dependencies(
            first={"/a": ["/b"]},
            refined={"/a": ["/c"]},
            allowed_nodes={"/a", "/b", "/c"},
        )

        # Refine wins because it produced a non-empty adjacency for /a.
        assert merged == {"/a": ["/c"], "/b": [], "/c": []}

    def test_merge_refine_empty_does_not_destroy_first(self):
        merged = _merge_dependencies(
            first={"/a": ["/b"]},
            refined={"/a": []},
            allowed_nodes={"/a", "/b"},
        )

        assert merged == {"/a": ["/b"], "/b": []}

    def test_merge_filters_foreign_sources_and_targets(self):
        merged = _merge_dependencies(
            first={"/a": ["/foreign"], "/foreign": ["/b"]},
            refined={"/b": ["/alien"]},
            allowed_nodes={"/a", "/b"},
        )

        # Foreign sources are dropped; foreign targets are removed from lists.
        assert merged == {"/a": [], "/b": []}


class TestParseLlmJsonHelper:
    def test_parse_llm_json_helper_strips_prose_around_json(self):
        result = _parse_llm_json('text {"a": ["b"]} more', first_pass=False)

        assert result == ({"a": ["b"]}, [])

    def test_parse_llm_json_helper_rejects_non_dict(self):
        with pytest.raises(LLMResponseParseError) as exc_info:
            _parse_llm_json("[1, 2]", first_pass=False)

        assert exc_info.value.reason == "not a dict"

    def test_parse_llm_json_helper_validates_shape(self):
        with pytest.raises(LLMResponseParseError) as exc_info:
            _parse_llm_json('{"a": "not_a_list"}', first_pass=False)

        assert "shape mismatch" in exc_info.value.reason

    @pytest.mark.parametrize(
        "dependencies_value",
        [42, ["/x"], "a string", None],
        ids=["int", "list", "string", "null"],
    )
    def test_parse_llm_json_first_pass_non_dict_dependencies_raises_parse_error(self, dependencies_value):
        # A first-pass response whose "dependencies" is not a dict must surface
        # as LLMResponseParseError (mapped to a clean ClickException by the
        # discover handler), not an unhandled AttributeError from .items().
        raw = json.dumps({"dependencies": dependencies_value, "uncertain": []})

        with pytest.raises(LLMResponseParseError) as exc_info:
            _parse_llm_json(raw, first_pass=True)

        assert "shape mismatch" in exc_info.value.reason

    def test_parse_llm_json_refine_unwraps_wrapped_dependencies(self):
        # The refine-pass prompt asks for a flat {path: [deps]} map, but the
        # model occasionally reuses the first-pass envelope {"dependencies": {...}}
        # under multi-turn context. The refine parser unwraps this single-key
        # envelope before shape validation.
        raw = json.dumps({"dependencies": {"/users": ["/users/{id}"]}})

        result = _parse_llm_json(raw, first_pass=False)

        assert result == ({"/users": ["/users/{id}"]}, [])

    def test_parse_llm_json_refine_does_not_unwrap_when_extra_keys_present(self):
        # The unwrap is narrow: only a single "dependencies" key is normalized.
        # Extra keys mean the model produced genuine garbage; the shape validator
        # catches it as before.
        raw = json.dumps({"dependencies": {"/users": ["/x"]}, "extra": "noise"})

        with pytest.raises(LLMResponseParseError) as exc_info:
            _parse_llm_json(raw, first_pass=False)

        assert "shape mismatch" in exc_info.value.reason
