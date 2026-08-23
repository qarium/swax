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
import shutil

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
    "git:\n  url: https://example.com/repo.git\n  location: specs/\nspecs:\n  type: openapi\n  location: specs\n"
)

UNSAFE_CONFIG_YML = (
    "git:\n  url: https://example.com/repo.git\n  location: specs/\nspecs:\n  type: openapi\n  location: .\n"
)

BASELINE_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /users:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

UPDATED_SPEC = BASELINE_SPEC + "  /billing:\n" + "    get:\n" + "      responses: {'200': {description: ok}}\n"

LEGACY_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /legacy:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

API_SPEC_WITH_SHARED = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /users:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
    "  /shared:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

LEGACY_SPEC_WITH_SHARED = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /shared:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
    "  /legacy:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

BILLING_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Billing, version: 1.0.0}\n"
    "paths:\n"
    "  /billing:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
    "components:\n"
    "  schemas:\n"
    "    Billing:\n"
    "      type: object\n"
)

BILLING_SPEC_WITH_DATE = (
    "openapi: 3.0.0\n"
    "info: {title: Billing, version: 1.0.0}\n"
    "paths:\n"
    "  /billing:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
    "components:\n"
    "  schemas:\n"
    "    Billing:\n"
    "      type: object\n"
    "      properties:\n"
    "        created:\n"
    "          type: string\n"
    "          example: 2024-01-31\n"
)

SHARED_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Shared, version: 1.0.0}\n"
    "paths:\n"
    "  /shared:\n"
    "    get:\n"
    "      responses: {'200': {description: ok}}\n"
)

# Valid YAML that fails prance resolution — a plausible WIP spec whose $ref
# target is missing. Byte-identical locally and remotely in the tests below.
UNPARSEABLE_UNTOUCHED_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Wip, version: 1.0.0}\n"
    "paths:\n"
    "  /wip:\n"
    "    get:\n"
    "      responses:\n"
    "        '200':\n"
    "          $ref: './missing.yaml#/responses/OK'\n"
)

MODIFIED_RESPONSE_SPEC = (
    "openapi: 3.0.0\n"
    "info: {title: Test, version: 1.0.0}\n"
    "paths:\n"
    "  /users:\n"
    "    get:\n"
    "      responses: {'200': {description: 'ok v2'}}\n"
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


def _patch_capturing_client(mocker, response: str) -> dict:
    captured: dict = {}

    class _CapturingClient:
        def ask(self, system, user):
            captured["system"] = system
            captured["user"] = user
            return response

    mocker.patch(BUILD_CLIENT, return_value=_CapturingClient())
    return captured


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
        # /legacy is a graph key AND a dangling adjacency target — the run must
        # drop the key and scrub the reference (an assertion against a graph
        # not mentioning /legacy would pass with pruning disabled).
        graph_file = _write_graph(tmp_path, "/users:\n- /legacy\n/orders:\n- /users\n/legacy:\n- /users\n")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        output = run_update(tmp_path)

        assert output == "Removed:\n  - legacy.yaml\nTraceability graph: rebuilt"
        client_tripwire.assert_not_called()
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": [],
            "/orders": ["/users"],
        }
        assert not (tmp_path / "specs" / "legacy.yaml").exists()

    def test_run_update_keeps_endpoints_still_declared_by_surviving_specs(self, update_project, mocker, tmp_path):
        # /shared is declared by BOTH the removed legacy.yaml and the surviving
        # api.yaml — it stays live, only /legacy (absent from the whole remote
        # tree) is pruned.
        graph_file = _write_graph(tmp_path, "/users:\n- /shared\n/shared:\n- /users\n/legacy:\n- /users\n")
        (tmp_path / "specs" / "api.yaml").write_text(API_SPEC_WITH_SHARED, encoding="utf-8")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC_WITH_SHARED, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": API_SPEC_WITH_SHARED})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        output = run_update(tmp_path)

        assert output == "Removed:\n  - legacy.yaml\nTraceability graph: rebuilt"
        client_tripwire.assert_not_called()
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/shared"],
            "/shared": ["/users"],
        }

    def test_run_update_keeps_endpoints_dropped_by_modified_spec_when_a_surviving_spec_declares_them(
        self, update_project, mocker, tmp_path
    ):
        # /shared is dropped by the MODIFIED api.yaml but still declared by the
        # unchanged b.yaml — the incremental branch must reconcile per-pair
        # removals like whole-file removals: /shared stays in the universe and
        # the graph, and never reaches the LLM as a removal.
        graph_file = _write_graph(tmp_path, "/users:\n- /shared\n/shared:\n- /users\n")
        (tmp_path / "specs" / "api.yaml").write_text(API_SPEC_WITH_SHARED, encoding="utf-8")
        (tmp_path / "specs" / "b.yaml").write_text(SHARED_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC, "b.yaml": SHARED_SPEC})
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/shared"], "/shared": ["/users"]}')

        output = run_update(tmp_path)

        assert output == "Updated:\n  - api.yaml\nTraceability graph: rebuilt"
        assert '"removed": []' in captured["user"]
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/shared"],
            "/shared": ["/users"],
        }

    def test_run_update_removals_only_skips_unparseable_untouched_spec(self, update_project, mocker, tmp_path):
        # wip.yaml is byte-identical locally and remotely but unresolvable —
        # untouched specs are outside the pinned parse scope, so they must
        # never abort the run: the mirror applies and the prune proceeds.
        graph_file = _write_graph(tmp_path, "/users:\n- /legacy\n/legacy:\n- /users\n")
        specs = tmp_path / "specs"
        (specs / "wip.yaml").write_text(UNPARSEABLE_UNTOUCHED_SPEC, encoding="utf-8")
        (specs / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC, "wip.yaml": UNPARSEABLE_UNTOUCHED_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        output = run_update(tmp_path)

        assert output == "Removed:\n  - legacy.yaml\nTraceability graph: rebuilt"
        client_tripwire.assert_not_called()
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {"/users": []}
        assert (specs / "wip.yaml").read_text(encoding="utf-8") == UNPARSEABLE_UNTOUCHED_SPEC
        assert not (specs / "legacy.yaml").exists()

    def test_run_update_pure_additions_never_parses_untouched_specs(self, update_project, mocker, tmp_path):
        # Nothing can be dropped, so no untouched survivor is read at all —
        # an unparseable one is not even noticed by the incremental branch.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        specs = tmp_path / "specs"
        (specs / "wip.yaml").write_text(UNPARSEABLE_UNTOUCHED_SPEC, encoding="utf-8")
        remote = _make_remote(
            tmp_path,
            {"api.yaml": BASELINE_SPEC, "wip.yaml": UNPARSEABLE_UNTOUCHED_SPEC, "billing.yaml": BILLING_SPEC},
        )
        _patch_clone(mocker, remote)
        calls = _patch_client(mocker, '{"/users": ["/orders"], "/billing": ["/users"]}')

        output = run_update(tmp_path)

        assert calls["ask"] == 1
        assert output == "Added:\n  - billing.yaml\nTraceability graph: rebuilt"
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
            "/billing": ["/users"],
        }

    def test_run_update_keeps_endpoints_dropped_by_modified_spec_when_an_added_spec_declares_them(
        self, update_project, mocker, tmp_path
    ):
        # /shared is dropped by the MODIFIED api.yaml but declared by the
        # ADDED b.yaml — the reconciliation set covers the added specs too,
        # so /shared never reaches the LLM as a removal.
        graph_file = _write_graph(tmp_path, "/users:\n- /shared\n/shared:\n- /users\n")
        (tmp_path / "specs" / "api.yaml").write_text(API_SPEC_WITH_SHARED, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC, "b.yaml": SHARED_SPEC})
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/shared"], "/shared": ["/users"]}')

        output = run_update(tmp_path)

        assert output == "Added:\n  - b.yaml\nUpdated:\n  - api.yaml\nTraceability graph: rebuilt"
        assert '"removed": []' in captured["user"]
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/shared"],
            "/shared": ["/users"],
        }

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

    def test_run_update_added_spec_file_feeds_endpoints_and_schemas_into_revision(
        self, update_project, mocker, tmp_path
    ):
        # A brand-new spec file in the remote: its endpoints join the revision
        # universe (becoming graph nodes) and its schemas reach the prompt.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC, "billing.yaml": BILLING_SPEC})
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/orders"], "/orders": [], "/billing": ["/users"]}')

        output = run_update(tmp_path)

        assert output == "Added:\n  - billing.yaml\nTraceability graph: rebuilt"
        assert '"/billing"' in captured["user"]
        assert "Billing" in captured["user"]
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
            "/billing": ["/users"],
        }
        assert (tmp_path / "specs" / "billing.yaml").read_text(encoding="utf-8") == BILLING_SPEC

    def test_run_update_added_spec_with_yaml_date_scalar_completes_revision(self, update_project, mocker, tmp_path):
        # YAML parses the unquoted example into a datetime.date — the prompt
        # payload must serialize it (default=str), not raise a raw TypeError
        # out of the rebuild block.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC, "billing.yaml": BILLING_SPEC_WITH_DATE})
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/orders"], "/orders": [], "/billing": []}')

        output = run_update(tmp_path)

        assert output == "Added:\n  - billing.yaml\nTraceability graph: rebuilt"
        assert "2024-01-31" in captured["user"]
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
            "/billing": [],
        }
        assert (tmp_path / "specs" / "billing.yaml").read_text(encoding="utf-8") == BILLING_SPEC_WITH_DATE

    def test_run_update_added_spec_endpoints_are_deduplicated_across_files(self, update_project, mocker, tmp_path):
        # Two added spec files both declaring /billing: the prompt endpoints
        # are their union — /billing appears once, not once per file.
        _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(
            tmp_path,
            {"api.yaml": BASELINE_SPEC, "billing.yaml": BILLING_SPEC, "billing2.yaml": BILLING_SPEC},
        )
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/orders"], "/orders": [], "/billing": ["/users"]}')

        run_update(tmp_path)

        assert '"endpoints": ["/billing"]' in captured["user"]
        assert '"endpoints": ["/billing", "/billing"]' not in captured["user"]

    def test_run_update_prompt_carries_modified_endpoint_descriptions(self, update_project, mocker, tmp_path):
        # A changed response description classifies as a modification (not an
        # added endpoint); its description must reach the revision prompt.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": MODIFIED_RESPONSE_SPEC})
        _patch_clone(mocker, remote)
        captured = _patch_capturing_client(mocker, '{"/users": ["/orders"], "/orders": []}')

        output = run_update(tmp_path)

        assert output == "Updated:\n  - api.yaml\nTraceability graph: rebuilt"
        assert '"modified"' in captured["user"]
        assert "get responses 200 description changed" in captured["user"]
        assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {
            "/users": ["/orders"],
            "/orders": [],
        }


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

    def test_run_update_wrong_llm_json_shape_wraps_into_graph_rebuild_failed(self, update_project, mocker, tmp_path):
        # Valid JSON, wrong shape (a nested mapping instead of dict[str, list[str]])
        # — the shape check, not the JSON decoder, rejects it.
        _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        _patch_client(mocker, '{"dependencies": {"/users": ["/orders"]}}')

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "shape mismatch" in exc_info.value.reason
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC

    def test_run_update_graph_write_failure_restores_specs_and_wraps(self, update_project, mocker, tmp_path):
        graph_content = "/users:\n- /orders\n/orders: []\n"
        graph_file = _write_graph(tmp_path, graph_content)
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        mocker.patch(
            "swax.applications.update.save_traceability_atomically.save_traceability",
            side_effect=OSError("disk full"),
        )
        _patch_client(mocker, '{"/users": ["/orders"], "/orders": []}')

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "disk full" in exc_info.value.reason
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        assert graph_file.read_text(encoding="utf-8") == graph_content
        assert not (tmp_path / ".swax" / "traceability.yml.tmp").exists()

    def test_run_update_corrupt_graph_file_wraps_into_graph_rebuild_failed(self, update_project, mocker, tmp_path):
        # A malformed traceability.yml fails inside the rebuild block (the
        # prune branch loads it there) — wrapped like every other rebuild
        # failure, not a raw yaml traceback.
        _write_graph(tmp_path, "broken: [unclosed\n")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "expected" in exc_info.value.reason.lower() or "yaml" in exc_info.value.reason.lower()
        assert (tmp_path / "specs" / "legacy.yaml").exists()

    def test_run_update_corrupt_graph_file_in_additions_branch_wraps_into_graph_rebuild_failed(
        self, update_project, mocker, tmp_path
    ):
        # The same malformed traceability.yml in the incremental branch: the
        # graph is loaded inside the rebuild block there too, so the failure
        # is wrapped and the specs restored — never a raw yaml traceback.
        _write_graph(tmp_path, "broken: [unclosed\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "expected" in exc_info.value.reason.lower() or "yaml" in exc_info.value.reason.lower()
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        client_tripwire.assert_not_called()

    def test_run_update_non_utf8_graph_file_in_additions_branch_wraps_into_graph_rebuild_failed(
        self, update_project, mocker, tmp_path
    ):
        # A binary-corrupt traceability.yml fails decode inside the rebuild
        # block — wrapped like every other rebuild failure, never a raw
        # UnicodeDecodeError traceback.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        graph_file.write_bytes(b"/users:\n- /orders\n\xff\xfe\xfa")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "utf-8" in str(exc_info.value.reason)
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        client_tripwire.assert_not_called()

    def test_run_update_non_utf8_graph_file_in_prune_branch_wraps_into_graph_rebuild_failed(
        self, update_project, mocker, tmp_path
    ):
        # The same binary corruption in the removals-only branch: the prune
        # load happens inside the rebuild block too.
        graph_file = _write_graph(tmp_path, "/users:\n- /orders\n/orders: []\n")
        graph_file.write_bytes(b"/users:\n- /orders\n\xff\xfe\xfa")
        (tmp_path / "specs" / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)

        with pytest.raises(GraphRebuildFailedError):
            run_update(tmp_path)

        assert (tmp_path / "specs" / "legacy.yaml").exists()

    def test_run_update_non_string_graph_values_wraps_into_graph_rebuild_failed(self, update_project, mocker, tmp_path):
        # A syntactically valid graph whose adjacency holds a non-string
        # scalar fails TraceabilityGraph validation inside the rebuild block —
        # wrapped, not a raw pydantic ValidationError traceback.
        _write_graph(tmp_path, "/users: 1\n")
        remote = _make_remote(tmp_path, {"api.yaml": UPDATED_SPEC})
        _patch_clone(mocker, remote)
        client_tripwire = mocker.patch(BUILD_CLIENT)

        with pytest.raises(GraphRebuildFailedError) as exc_info:
            run_update(tmp_path)

        assert "Input should be a valid string" in str(exc_info.value.reason)
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        client_tripwire.assert_not_called()


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

    def test_run_update_missing_local_specs_dir_mirrors_and_delegates(self, update_project, mocker, tmp_path):
        # First-ever mirror into an absent specs directory: every remote file
        # is added, the swap creates the directory, and the first build is
        # delegated to run_discover.
        shutil.rmtree(tmp_path / "specs")
        remote = _make_remote(tmp_path, {"api.yaml": BASELINE_SPEC})
        _patch_clone(mocker, remote)
        mock_discover = mocker.patch(RUN_DISCOVER)

        output = run_update(tmp_path)

        mock_discover.assert_called_once_with(tmp_path)
        assert output == "Added:\n  - api.yaml\nTraceability graph: built"
        assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
        assert not (tmp_path / ".specs-staging").exists()
        assert not (tmp_path / ".specs.backup").exists()
