"""Integration tests — end-to-end ``swax update``.

These tests drive the full Click entry point (the ``main`` group with
``update`` lazily registered) through CliRunner against a real on-disk
project rooted at ``tmp_path``. The update handler resolves the project root
from ``Path.cwd()``, so each test chdir's into its own isolated tmp project.

Only the external boundaries are mocked: ``clone_specs`` (the git clone) and
``build_llm_client`` (the LLM transport), both patched at their use site in
``run_update``. Everything else runs for real — the config is loaded, specs
are compared byte-level, the staging swap moves directories, the traceability
graph is pruned, and the summary is echoed. The three scenarios cover the
empty diff (up-to-date message, exit 0, no LLM), the removals-only prune
(deterministic graph shrink without an LLM call), and the missing-credentials
abort (exit 1 with specs and graph untouched).
"""

import pathlib

import swax.cli.__main__  # noqa: F401 -- side effect: register init/discover/plan/update on main
import yaml
from click.testing import CliRunner
from swax.cli import main

# External boundaries patched at their use site in run_update (no live clone / API).
BUILD_CLIENT = "swax.applications.update.run_update.build_llm_client"
CLONE_SPECS = "swax.applications.update.run_update.clone_specs"

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

LEGACY_SPEC = """\
openapi: 3.0.0
info:
  title: Test
  version: 1.0.0
paths:
  /legacy:
    get:
      responses:
        '200':
          description: ok
"""

# The fresh clone adds the /orders endpoint so the diff has an addition and
# update would need LLM credentials.
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


def _materialize_project(tmp_path: pathlib.Path, *, with_legacy: bool = False) -> None:
    """Write .swax/config.yml, the baseline spec, and optional extras."""
    swax_dir = tmp_path / ".swax"
    swax_dir.mkdir(exist_ok=True)
    (swax_dir / "config.yml").write_text(CONFIG_YML, encoding="utf-8")
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(exist_ok=True)
    (specs_dir / "api.yaml").write_text(BASELINE_SPEC, encoding="utf-8")
    if with_legacy:
        (specs_dir / "legacy.yaml").write_text(LEGACY_SPEC, encoding="utf-8")


def _fresh_root(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    """Create a fresh clone dir carrying the given spec files."""
    fresh = tmp_path / "fresh"
    fresh.mkdir(exist_ok=True)
    for rel, content in files.items():
        (fresh / rel).write_text(content, encoding="utf-8")
    return fresh


def _patch_clone(mocker, fresh_root: pathlib.Path):
    """Mock clone_specs so the with-block yields fresh_root."""
    mock_clone = mocker.patch(CLONE_SPECS)
    mock_clone.return_value.__enter__.return_value = fresh_root
    mock_clone.return_value.__exit__.return_value = False
    return mock_clone


def test_swax_update_no_changes_reports_up_to_date(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    _materialize_project(tmp_path)
    _patch_clone(mocker, _fresh_root(tmp_path, {"api.yaml": BASELINE_SPEC}))
    mock_build = mocker.patch(BUILD_CLIENT)

    result = CliRunner().invoke(main, ["update"])

    assert result.exit_code == 0, result.output
    assert "Specs are up to date." in result.output
    mock_build.assert_not_called()


def test_swax_update_removals_only_prunes_graph_without_llm(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    _materialize_project(tmp_path, with_legacy=True)
    graph_file = tmp_path / ".swax" / "traceability.yml"
    graph_file.write_text("/users:\n- /legacy\n/legacy:\n- /users\n", encoding="utf-8")
    # The fresh clone no longer carries legacy.yaml.
    _patch_clone(mocker, _fresh_root(tmp_path, {"api.yaml": BASELINE_SPEC}))
    mock_build = mocker.patch(BUILD_CLIENT)

    result = CliRunner().invoke(main, ["update"])

    assert result.exit_code == 0, result.output
    assert "Removed:" in result.output
    assert "- legacy.yaml" in result.output
    assert "Traceability graph: rebuilt" in result.output
    mock_build.assert_not_called()
    assert yaml.safe_load(graph_file.read_text(encoding="utf-8")) == {"/users": []}
    assert not (tmp_path / "specs" / "legacy.yaml").exists()
    assert not (tmp_path / ".specs-staging").exists()
    assert not (tmp_path / ".specs.backup").exists()


def test_swax_update_missing_env_vars_aborts_before_any_mutation(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    _materialize_project(tmp_path)
    graph_file = tmp_path / ".swax" / "traceability.yml"
    graph_content = "/users:\n- /orders\n"
    graph_file.write_text(graph_content, encoding="utf-8")
    _patch_clone(mocker, _fresh_root(tmp_path, {"api.yaml": FRESH_SPEC_WITH_ORDERS}))
    mock_build = mocker.patch(BUILD_CLIENT)

    result = CliRunner().invoke(main, ["update"])

    assert result.exit_code == 1, result.output
    assert "Missing env vars" in result.output
    mock_build.assert_not_called()
    # Credentials are validated before any mutation — specs and graph untouched.
    assert (tmp_path / "specs" / "api.yaml").read_text(encoding="utf-8") == BASELINE_SPEC
    assert graph_file.read_text(encoding="utf-8") == graph_content
