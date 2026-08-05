"""Integration tests — end-to-end ``swax plan`` (task 8).

These tests drive the full Click entry point (the ``main`` group with ``plan``
lazily registered) through CliRunner against a real on-disk project rooted at
``tmp_path``. The plan handler resolves the project root from ``Path.cwd()``, so
each test chdir's into its own isolated tmp project.

Only the external boundaries are mocked: ``clone_specs`` (the git clone) and
``build_llm_client`` (the LLM transport), both patched at their use site in
``run_plan``. Everything else runs for real — Prance parses the specs, the
deepdiff/classify pipeline runs, the traceability graph is read, the prompt
builders run, the defensive JSON parse runs, and the Markdown render runs. The
three scenarios cover the happy path (changed spec → rendered Impact Report,
exit 0), the no-change short-circuit (LLM never called), and the missing-graph
existence check (mapped to the ``swax discover`` hint, exit 1).
"""

import json
import pathlib

import swax.cli.__main__  # noqa: F401 -- side effect: register init/discover/plan on main
from click.testing import CliRunner
from swax.cli import main

# External boundaries patched at their use site in run_plan (no live clone / API).
BUILD_CLIENT = "swax.applications.plan.run_plan.build_llm_client"
CLONE_SPECS = "swax.applications.plan.run_plan.clone_specs"

ENV_VARS = {
    "SWAX_LLM_MODEL": "claude-test-model",
    "SWAX_LLM_PROTOCOL": "anthropic",
    "SWAX_LLM_BASE_URL": "https://example.com",
    "SWAX_LLM_TOKEN": "test-token",
}

# config.specs.location is "specs"; config.git.location is "specs/" (unused —
# clone_specs is mocked). The traceability graph is a minimal /a -> /b edge.
CONFIG_YML = """\
git:
  url: https://example.com/repo.git
  location: specs/
specs:
  type: openapi
  location: specs
"""

TRACE_YML = "/a:\n- /b\n"

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

# The fresh clone adds the /orders endpoint so the diff pipeline reports a
# change and run_plan reaches the LLM.
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


def _impact_json(**overrides) -> str:
    payload = {
        "summary": "added /orders endpoint",
        "risk": "HIGH",
        "modified": [],
        "affected": ["/orders"],
        "requirements": ["test /orders"],
        "checklist": ["smoke /orders"],
    }
    payload.update(overrides)
    return json.dumps(payload)


def _materialize_project(tmp_path: pathlib.Path, *, with_traceability: bool = True) -> None:
    """Write .swax/config.yml (+ optional traceability.yml) and the baseline spec."""
    swax_dir = tmp_path / ".swax"
    swax_dir.mkdir(exist_ok=True)
    (swax_dir / "config.yml").write_text(CONFIG_YML, encoding="utf-8")
    if with_traceability:
        (swax_dir / "traceability.yml").write_text(TRACE_YML, encoding="utf-8")
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(exist_ok=True)
    (specs_dir / "api.yaml").write_text(BASELINE_SPEC, encoding="utf-8")


def _fresh_root(tmp_path: pathlib.Path, spec_text: str) -> pathlib.Path:
    """Create a fresh clone dir carrying api.yaml with the given spec text."""
    fresh = tmp_path / "fresh"
    fresh.mkdir(exist_ok=True)
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


def test_swax_plan_end_to_end_with_mocked_llm(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    _materialize_project(tmp_path, with_traceability=True)
    fresh_root = _fresh_root(tmp_path, FRESH_SPEC_WITH_ORDERS)
    _patch_clone(mocker, fresh_root)
    mock_build = _patch_llm(mocker, _impact_json())

    result = CliRunner().invoke(main, ["--env-file", ".env", "plan"])

    assert result.exit_code == 0, result.output
    # Generic markers alone also appear in the no-change render, so assert the
    # LLM was actually consulted and that LLM-provided content reached stdout —
    # this is what distinguishes the change path from the short-circuit.
    mock_build.assert_called_once()
    assert "added /orders endpoint" in result.output
    assert "/orders" in result.output
    assert "smoke /orders" in result.output


def test_swax_plan_no_changes_short_circuits(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    _materialize_project(tmp_path, with_traceability=True)
    # The fresh clone is identical to the baseline → no changes → LLM untouched.
    fresh_root = _fresh_root(tmp_path, BASELINE_SPEC)
    _patch_clone(mocker, fresh_root)
    mock_build = mocker.patch(BUILD_CLIENT)

    result = CliRunner().invoke(main, ["--env-file", ".env", "plan"])

    assert result.exit_code == 0, result.output
    assert "No changes detected" in result.output
    mock_build.assert_not_called()


def test_swax_plan_missing_traceability_maps_to_hint(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    _materialize_project(tmp_path, with_traceability=False)
    _patch_clone(mocker, _fresh_root(tmp_path, FRESH_SPEC_WITH_ORDERS))
    _patch_llm(mocker, _impact_json())

    result = CliRunner().invoke(main, ["--env-file", ".env", "plan"])

    assert result.exit_code == 1, result.output
    assert "Traceability graph not found" in result.output
    assert "swax discover" in result.output
