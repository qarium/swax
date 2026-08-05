"""Logic tests for run_plan (task 6).

build_llm_client and clone_specs are mocked at their import points
(swax.applications.plan.run_plan.*) so no live LLM is contacted and no clone is
performed; parse_spec runs for real against local, self-contained OpenAPI
fixtures (prance resolves $ref offline). The scenarios cover the no-change
short-circuit (LLM never called), the missing-graph existence check, the
MEDIUM risk fallback, the defensive parse failures, propagation of clone
errors, no-secret-leak, and direct unit coverage of the _diff_and_classify,
_build_graph_context, and _parse_impact_report helpers.
"""

import json
import logging
import pathlib
import sys

import pytest
from swax.applications.plan import run_plan
from swax.applications.plan.run_plan import (
    _build_graph_context,
    _diff_and_classify,
    _parse_impact_report,
)
from swax.git import RepositoryCloneError, SpecsNotFoundError
from swax.llm import LLMResponseParseError
from swax.traceability import TraceabilityGraph, TraceabilityGraphMissingError

BUILD_CLIENT = "swax.applications.plan.run_plan.build_llm_client"
CLONE_SPECS = "swax.applications.plan.run_plan.clone_specs"

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

TRACE_YML = "/users:\n- /orders\n"

BASELINE_SPEC = """\
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
"""

FRESH_SPEC_WITH_ORDERS = """\
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
  /orders:
    get:
      responses:
        '200':
          description: ok
"""


@pytest.fixture
def plan_project(tmp_path, monkeypatch):
    """Materialize a minimal project: .swax/config.yml + traceability.yml + baseline spec + env."""
    swax_dir = tmp_path / ".swax"
    swax_dir.mkdir()
    (swax_dir / "config.yml").write_text(CONFIG_YML, encoding="utf-8")
    (swax_dir / "traceability.yml").write_text(TRACE_YML, encoding="utf-8")
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "api.yaml").write_text(BASELINE_SPEC, encoding="utf-8")
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    return tmp_path


def _fresh_root(tmp_path: pathlib.Path, spec_text: str, name: str = "fresh") -> pathlib.Path:
    """Create a fresh specs dir with an api.yaml carrying the given spec text."""
    fresh = tmp_path / name
    fresh.mkdir()
    (fresh / "api.yaml").write_text(spec_text, encoding="utf-8")
    return fresh


def _patch_clone(mocker, fresh_root: pathlib.Path):
    """Mock clone_specs so the with-block yields fresh_root."""
    mock_clone = mocker.patch(CLONE_SPECS)
    mock_clone.return_value.__enter__.return_value = fresh_root
    mock_clone.return_value.__exit__.return_value = False
    return mock_clone


def _patch_llm(mocker, response_text: str):
    """Mock build_llm_client so client.ask returns response_text."""
    mock_build = mocker.patch(BUILD_CLIENT)
    mock_build.return_value.ask.return_value = response_text
    return mock_build


def _impact_json(**overrides) -> str:
    payload = {
        "summary": "added an endpoint",
        "risk": "HIGH",
        "modified": [],
        "affected": ["/orders"],
        "requirements": ["test /orders"],
        "checklist": ["smoke /orders"],
    }
    payload.update(overrides)
    return json.dumps(payload)


class TestRunPlanNoChanges:
    def test_run_plan_no_changes_skips_llm_and_returns_low_risk(self, plan_project, tmp_path, mocker):
        fresh_root = _fresh_root(tmp_path, BASELINE_SPEC)
        _patch_clone(mocker, fresh_root)
        mock_build = mocker.patch(BUILD_CLIENT)

        markdown = run_plan(project_root=plan_project)

        assert "No changes detected" in markdown
        assert "LOW" in markdown
        mock_build.assert_not_called()


class TestRunPlanMissingGraph:
    def test_run_plan_raises_missing_graph_when_traceability_absent(self, plan_project):
        (plan_project / ".swax" / "traceability.yml").unlink()

        with pytest.raises(TraceabilityGraphMissingError) as exc_info:
            run_plan(project_root=plan_project)

        assert exc_info.value.path.name == "traceability.yml"


class TestRunPlanRiskFallback:
    def test_run_plan_invalid_risk_falls_back_to_medium(self, plan_project, tmp_path, mocker, caplog):
        fresh_root = _fresh_root(tmp_path, FRESH_SPEC_WITH_ORDERS)
        _patch_clone(mocker, fresh_root)
        _patch_llm(mocker, _impact_json(risk="EXTREME"))
        caplog.set_level(logging.WARNING, logger="swax.applications.plan.run_plan")

        markdown = run_plan(project_root=plan_project)

        assert "MEDIUM" in markdown
        assert "EXTREME" not in markdown
        assert any("risk" in record.getMessage() and record.levelno == logging.WARNING for record in caplog.records)


class TestRunPlanParseAndCloneErrors:
    def test_run_plan_propagates_llm_response_parse_error_on_bad_json(self, plan_project, tmp_path, mocker):
        fresh_root = _fresh_root(tmp_path, FRESH_SPEC_WITH_ORDERS)
        _patch_clone(mocker, fresh_root)
        _patch_llm(mocker, "not json at all")

        with pytest.raises(LLMResponseParseError):
            run_plan(project_root=plan_project)

    def test_run_plan_propagates_repository_clone_error(self, plan_project, mocker):
        mock_clone = mocker.patch(CLONE_SPECS)
        mock_clone.side_effect = RepositoryCloneError(
            url="https://example.com/repo.git",
            reason="boom",
        )

        with pytest.raises(RepositoryCloneError):
            run_plan(project_root=plan_project)

    def test_run_plan_propagates_specs_not_found(self, plan_project, mocker):
        mock_clone = mocker.patch(CLONE_SPECS)
        mock_clone.side_effect = SpecsNotFoundError(path=pathlib.Path("/missing"))

        with pytest.raises(SpecsNotFoundError):
            run_plan(project_root=plan_project)


class TestRunPlanNoSecretLeak:
    def test_run_plan_markdown_contains_no_llm_token(self, plan_project, tmp_path, mocker):
        fresh_root = _fresh_root(tmp_path, FRESH_SPEC_WITH_ORDERS)
        _patch_clone(mocker, fresh_root)
        _patch_llm(mocker, _impact_json())

        markdown = run_plan(project_root=plan_project)

        assert "test-token" not in markdown
        assert "SWAX_LLM_TOKEN" not in markdown


class TestDiffAndClassifyHelper:
    def test_both_sides_merges_added_and_modified(self):
        baseline = {"api.yaml": {"paths": {"/users": {"get": {"summary": "a"}}}}}
        fresh = {"api.yaml": {"paths": {"/users": {"get": {"summary": "b"}}, "/orders": {}}}}

        merged = _diff_and_classify(baseline, fresh)

        assert merged.added == ["/orders"]
        assert "/users" in merged.modified
        assert merged.removed == []
        assert merged.has_changes() is True

    def test_fresh_only_reads_paths_directly_as_added(self):
        # A spec present only in fresh: diffing against {} would only surface the
        # top-level `paths` key, so paths must be read directly.
        baseline = {}
        fresh = {"new.yaml": {"paths": {"/a": {}, "/b": {}}}}

        merged = _diff_and_classify(baseline, fresh)

        assert merged.added == ["/a", "/b"]
        assert merged.removed == []
        assert merged.modified == {}

    def test_baseline_only_reads_paths_directly_as_removed(self):
        baseline = {"old.yaml": {"paths": {"/x": {}, "/y": {}}}}
        fresh = {}

        merged = _diff_and_classify(baseline, fresh)

        assert merged.removed == ["/x", "/y"]
        assert merged.added == []
        assert merged.modified == {}

    def test_empty_inputs_yield_no_changes(self):
        merged = _diff_and_classify({}, {})

        assert merged.has_changes() is False
        assert merged.changed_paths() == []


class TestBuildGraphContextHelper:
    def test_no_trimming_under_threshold(self):
        graph = TraceabilityGraph(edges={"/a": ["/b"], "/c": []})

        ctx, affected = _build_graph_context(["/a", "/c"], ["/a"], graph)

        assert ctx == {"/a": ["/b"], "/c": []}
        assert affected == ["/a", "/c"]

    def test_trims_to_max_affected_changed_first(self, mocker):
        run_plan_module = sys.modules["swax.applications.plan.run_plan"]
        mocker.patch.object(run_plan_module, "_MAX_AFFECTED", 3)
        graph = TraceabilityGraph(edges={})
        affected = [f"/e{i}" for i in range(10)]
        changed = ["/e0", "/e5"]

        ctx, trimmed = _build_graph_context(affected, changed, graph)

        assert len(trimmed) == 3
        assert set(ctx) == {"/e0", "/e1", "/e5"}
        # Both changed paths survive the trim (changed-first policy); the
        # returned affected list is sorted.
        assert "/e0" in trimmed
        assert "/e5" in trimmed
        assert trimmed == sorted(trimmed)


class TestParseImpactReportHelper:
    def test_parses_valid_report(self):
        report = _parse_impact_report(_impact_json(risk="LOW"))

        assert report.risk == "LOW"
        assert report.summary == "added an endpoint"

    def test_strips_prose_around_json(self):
        report = _parse_impact_report("here you go: " + _impact_json() + " thanks")

        assert report.summary == "added an endpoint"

    def test_invalid_risk_falls_back_to_medium(self, caplog):
        caplog.set_level(logging.WARNING, logger="swax.applications.plan.run_plan")

        report = _parse_impact_report(_impact_json(risk="EXTREME"))

        assert report.risk == "MEDIUM"

    def test_rejects_non_dict(self):
        with pytest.raises(LLMResponseParseError):
            _parse_impact_report('["not", "an", "object"]')

    def test_rejects_missing_keys(self):
        with pytest.raises(LLMResponseParseError):
            _parse_impact_report(json.dumps({"summary": "s", "risk": "LOW"}))

    def test_rejects_wrong_value_type(self):
        with pytest.raises(LLMResponseParseError):
            _parse_impact_report(_impact_json(modified="not a list"))

    def test_rejects_bad_json(self):
        with pytest.raises(LLMResponseParseError):
            _parse_impact_report("not json at all")
