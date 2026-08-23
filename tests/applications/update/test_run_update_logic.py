"""Logic tests for run_update — the update transaction (task 10).

Exercises the full transaction against the real filesystem, the real
compare_specs / staged_specs_swap / parse_spec stack, and mocked boundaries
at the import points: clone_specs is replaced by a context manager yielding
a prepared directory, build_llm_client by a fake client that counts ask
calls, and run_discover / require_vars where a test isolates a layer.

Scenarios follow the design's flow list: empty diff, removals-only with and
without a graph file, incremental revision via a single ask, mixed diff with
whole-file-removal folding (review q1), delegated first build, and the
negative paths (missing credentials, unsafe location, clone failure, rebuild
failure with specs restored, partial first-build cleanup, bad LLM JSON) plus
the non-spec-file mirroring edge (q3) and the stale-staging guard.
"""

import contextlib
import pathlib

import pytest
import yaml
from swax.applications.update import GraphRebuildFailedError, run_update
from swax.config import MissingEnvironmentVariablesError
from swax.fs import UnsafeSpecsLocationError
from swax.git import RepositoryCloneError
from swax.llm import LLMCallError

ENV_VARS = {
    "SWAX_LLM_MODEL": "claude-test-model",
    "SWAX_LLM_PROTOCOL": "anthropic",
    "SWAX_LLM_BASE_URL": "https://example.com",
    "SWAX_LLM_TOKEN": "test-token",
}

CONFIG_YML = (
    "git:\n"
    "  url: https://example.com/repo.git\n"
    "  location: specs/\n"
    "specs:\n"
    "  type: openapi\n"
    "  location: specs\n"
)

UNSAFE_CONFIG_YML = (
    "git:\n"
    "  url: https://example.com/repo.git\n"
    "  location: specs/\n"
    "specs:\n"
    "  type: openapi\n"
    "  location: .\n"
)

BASELINE_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /users:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

UPDATED_SPEC = (
    BASELINE_SPEC
    + "  /billing:\n"
    + "    get:\n"
    + "      responses: {'200': {description: ok}}\n"
)

LEGACY_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /legacy:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

CLONE_SPECS = "swax.applications.update.run_update.clone_specs"
BUILD_CLIENT = "swax.applications.update.run_update.build_llm_client"
REQUIRE_VARS = "swax.applications.update.run_update.require_vars"
RUN_DISCOVER = "swax.applications.update.run_update.run_discover"


@pytest.fixture
def update_project(tmp_path, monkeypatch):
    (tmp_path / ".swax").mkdir()
    (tmp_path / ".swax" / "config.yml").write_text(CONFIG_YML, encoding="utf-8")
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "api.yaml").write_text(BASELINE_SPEC, encoding="utf-8")
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    return tmp_path


def _patch_clone(mocker, remote_root: pathlib.Path):
    @contextlib.contextmanager
    def _fake(repo_url, specs_location):
        yield remote_root

    return mocker.patch(CLONE_SPECS, side_effect=_fake)


def _patch_client(mocker, behavior):
    calls = {"ask": 0}

    class _FakeClient:
        def ask(self, system, user):
            calls["ask"] += 1
            if isinstance(behavior, Exception):
                raise behavior
            return behavior

    mocker.patch(BUILD_CLIENT, return_value=_FakeClient())
    return calls


def _make_remote(tmp_path, files: dict[str, str]) -> pathlib.Path:
    remote = tmp_path / "remote"
    for rel, content in files.items():
        path = remote / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return remote


def _write_graph(tmp_path, content: str) -> pathlib.Path:
    graph_file = tmp_path / ".swax" / "traceability.yml"
    graph_file.write_text(content, encoding="utf-8")
    return graph_file


class TestRunUpdatePositiveFlows:
    def test_run_update_empty_diff_returns_up_to_date_and_skips_llm(self, update_project, mocker, tmp_path):
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)
        require_tripwire = mocker.patch(REQUIRE_VARS)

        output = run_update(tmp_path)

        assert output == "Specs are up to date."
        client_tripwire.assert_not_called()
        require_tripwire.assert_not_called()
        assert not (tmp_path / ".swax" / "traceability.yml").exists()
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC

    def test_run_update_removals_only_prunes_graph_without_llm(self, update_project, mocker, tmp_path):
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders:\n- /users\n")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        output = run_update(tmp_path)

        assert output == "Removed:\n  - legacy.yaml\nTraceability graph: rebuilt"
        client_tripwire.assert_not_called()
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": ["/users"],
        }
        assert not (tmp_path / "specs" / "legacy.yaml").exists()

    def test_run_update_removals_only_without_graph_applies_specs_and_omits_status(
        self, update_project, mocker, tmp_path
    ):
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        output = run_update(tmp_path)

        assert output == "Removed:\n  - legacy.yaml"
        assert not (tmp_path / ".swax" / "traceability.yml").exists()
        client_tripwire.assert_not_called()

    def test_run_update_incremental_revises_graph_via_single_ask(self, update_project, mocker, tmp_path):
        # Every endpoint is a key — the run_discover invariant. The universe
        # formula is keys-only, so a target-only /orders would be dropped by
        # the filter and the expected graph would be unreachable.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        calls = _patch_client(
            mocker,
            '```json\n{"/users": ["/orders"], "/billing": ["/users"], "/ghost": ["/users"]}\n```',
        )

        output = run_update(tmp_path)

        assert calls["ask"] == 1
        assert output.endswith("Traceability graph: rebuilt")
        assert "Updated:\n  - api.yaml" in output
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
            "/billing": ["/users"],
        }
        assert "/ghost" not in graph_file.read_text(encoding="utf-8")

    def test_run_update_mixed_diff_prunes_removed_file_endpoints(self, update_project, mocker, tmp_path):
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n/legacy:\n- /users\n")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        calls = _patch_client(
            mocker,
            '{"/users": ["/orders"], "/legacy": ["/users"], "/billing": ["/users"]}',
        )

        output = run_update(tmp_path)

        assert calls["ask"] == 1
        assert output == "Updated:\n  - api.yaml\nRemoved:\n  - legacy.yaml\nTraceability graph: rebuilt"
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
            "/billing": ["/users"],
        }
        assert "/legacy" not in graph_file.read_text(encoding="utf-8")
        assert not (tmp_path / "specs" / "legacy.yaml").exists()

    def test_run_update_no_graph_delegates_to_run_discover(self, update_project, mocker, tmp_path):
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        mock_discover = mocker.patch(RUN_DISCOVER)

        output = run_update(tmp_path)

        mock_discover.assert_called_once_with(tmp_path)
        assert output == "Updated:\n  - api.yaml\nTraceability graph: built"


class TestRunUpdateNegativeFlows:
    def test_run_update_missing_env_vars_aborts_before_any_mutation(
        self, update_project, mocker, monkeypatch, tmp_path
    ):
        graph_content = "/users:\n- /orders\n/orders: []\n"
        _write_graph(tmp_path, graph_content)
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        monkeypatch.delenv("SWAX_LLM_TOKEN")

        with pytest.raises(MissingEnvironmentVariablesError):
            run_update(tmp_path)

        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        assert (tmp_path / ".swax" / "traceability.yml").read_text(encoding="utf-8") == graph_content

    def test_run_update_unsafe_location_propagates_before_clone(self, update_project, mocker, tmp_path):
        (tmp_path / ".swax" / "config.yml").write_text(UNSAFE_CONFIG_YML, encoding="utf-8")
        mock_clone = mocker.patch(CLONE_SPECS)

        with pytest.raises(UnsafeSpecsLocationError):
            run_update(tmp_path)

        mock_clone.assert_not_called()

    def test_run_update_clone_error_propagates_and_leaves_specs_untouched(self, update_project, mocker, tmp_path):
        graph_content = "/users:\n- /orders\n/orders: []\n"
        _write_graph(tmp_path, graph_content)
        mocker.patch(
            CLONE_SPECS,
            side_effect=RepositoryCloneError(url="https://example.com/repo.git", reason="boom"),
        )

        with pytest.raises(RepositoryCloneError):
            run_update(tmp_path)

        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        assert (tmp_path / ".swax" / "traceability.yml").read_text(encoding="utf-8") == graph_content
        assert not (tmp_path / ".specs-staging").exists()
        assert not (tmp_path / ".specs.backup").exists()

    def test_run_update_rebuild_failure_restores_specs_and_wraps(self, update_project, mocker, tmp_path):
        _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        _patch_client(mocker, LLMCallError(reason="boom"))

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "boom" in exc_info.value.reason
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        assert yaml.safe_load((tmp_path / ".swax" / "traceability.yml").read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
        }
        assert not (tmp_path / ".specs-staging").exists()
        assert not (tmp_path / ".specs.backup").exists()

    def test_run_update_failed_first_build_removes_partial_graph_file(self, update_project, mocker, tmp_path):
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)

        def _boom(project_root):
            (tmp_path / ".swax" / "traceability.yml").write_text("garbage: [", encoding="utf-8")
            raise LLMCallError(reason="boom")

        mocker.patch(RUN_DISCOVER, side_effect=_boom)

        with pytest.raises(GraphRebuildFailedError):
            run_update(tmp_path)

        assert not (tmp_path / ".swax" / "traceability.yml").exists()
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC

    def test_run_update_bad_llm_json_wraps_into_graph_rebuild_failed(self, update_project, mocker, tmp_path):
        _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        _patch_client(mocker, "Here is your graph: not-json-at-all")

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "Expecting" in exc_info.value.reason
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC


class TestRunUpdateEdgeCases:
    def test_run_update_ignores_non_spec_files_but_mirrors_them(self, update_project, mocker, tmp_path):
        # Every endpoint a key — otherwise the same-edges round-trip below
        # would drop a target-only endpoint.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        (tmp_path / "specs" / "README.md").write_text("readme v1", encoding="utf-8")
        remote = _make_remote(
            tmp_path,
            {
                "api.yaml": BASELINE_SPEC,
                "README.md": "readme v2",
                "docs/diagram.png": "PNGDATA",
            },
        )
        _patch_clone(mocker, remote)
        calls = _patch_client(mocker, '{"/users": ["/orders"], "/orders": []}')

        output = run_update(tmp_path)

        assert calls["ask"] == 1
        assert (tmp_path / "specs" / "README.md").read_text(encoding="utf-8") == "readme v2"
        assert (tmp_path / "specs" / "docs" / "diagram.png").read_text(encoding="utf-8") == "PNGDATA"
        assert "Updated:\n  - README.md" in output
        assert "Added:\n  - docs/diagram.png" in output
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
        }

    def test_run_update_removes_stale_staging_before_assembly(self, update_project, mocker, tmp_path):
        _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        stale = tmp_path / ".specs-staging"
        stale.mkdir()
        (stale / "junk.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        _patch_client(mocker, '{"/users": ["/orders"], "/orders": []}')

        run_update(tmp_path)

        assert not (tmp_path / ".specs-staging").exists()
        assert not (tmp_path / "specs" / "junk.yaml").exists()
