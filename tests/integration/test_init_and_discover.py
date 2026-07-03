"""Integration tests — end-to-end ``swax init`` + ``swax discover`` (task 23).

These tests drive the full Click entry point (the ``main`` group with ``init``
and ``discover`` lazily registered) through CliRunner against a real on-disk
project rooted at ``tmp_path``. Both handlers resolve the project root from
``Path.cwd()``, so each test chdir's into its own isolated tmp project.

``init`` runs against a real local git repository (no mock): GitPython shallow-
clones it, the specs are copied verbatim, and ``.swax/config.yml`` is persisted.
``discover`` runs the real two-pass orchestration with only the LLM transport
mocked at its use site — Prance parses the spec for real, the prompt builders and
traceability persistence run for real, and the resulting graph is written to
``.swax/traceability.yml``. The pipeline test chains both commands in one project.
"""

import pathlib

import swax.cli.__main__  # noqa: F401 -- side effect: register init/discover on main
import yaml
from click.testing import CliRunner
from swax.cli import main

from git import Repo

# LLM transport is patched at its use site inside run_discover (no live API call).
BUILD_CLIENT = "swax.applications.discover.run_discover.build_llm_client"

ENV_VARS = {
    "SWAX_LLM_MODEL": "claude-test-model",
    "SWAX_LLM_PROTOCOL": "anthropic",
    "SWAX_LLM_BASE_URL": "https://example.com",
    "SWAX_LLM_TOKEN": "test-token",
}

# A minimal, validator-friendly OpenAPI 3.0 spec with two paths and one schema.
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
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
"""

# First-pass (ask) and refine (ask_multi_turn) LLM responses — both valid JSON.
# The two responses are deliberately DIFFERENT so the persisted graph is proven
# to come from the refine pass: the first pass proposes /users/{id} -> /users,
# the refine pass revises it to /users -> /users/{id}. If run_discover ever
# persisted the first-pass dependency map instead of the refined result, the
# graph assertion below would fail.
FIRST_PASS_RESPONSE = '{"dependencies": {"/users/{id}": ["/users"]}, "uncertain": []}'
REFINE_RESPONSE = '{"/users": ["/users/{id}"]}'
EXPECTED_GRAPH = {"/users": ["/users/{id}"]}


def _make_remote_repo(path: pathlib.Path) -> str:
    """Init a local cloneable git repository with ``specs/api.yaml`` committed.

    Returns the clone URL (the repo's filesystem path); GitPython can shallow-
    clone a local working repository directly with ``depth=1``.
    """
    repo = Repo.init(path)
    # Set a repo-local committer identity so the commit does not depend on a
    # global/system git identity or ambient GIT_AUTHOR_*/GIT_COMMITTER_* env
    # vars (absent in many CI containers, which would make index.commit raise
    # GitCommandError "Author identity unknown").
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "swax-test")
        writer.set_value("user", "email", "swax-test@example.local")
    specs_dir = path / "specs"
    specs_dir.mkdir()
    (specs_dir / "api.yaml").write_text(OPENAPI_SPEC, encoding="utf-8")
    repo.index.add(["specs/api.yaml"])
    repo.index.commit("initial specs")
    return str(path)


def _wire_llm_mock(mock_build) -> None:
    """Configure the mocked LLM client with valid two-pass JSON responses."""
    client = mock_build.return_value
    client.ask.return_value = FIRST_PASS_RESPONSE
    client.ask_multi_turn.return_value = REFINE_RESPONSE


def test_swax_init_end_to_end_with_local_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo_url = _make_remote_repo(tmp_path / "remote")

    result = CliRunner().invoke(
        main,
        ["--env-file", str(tmp_path / ".env"), "init"],
        input=f"{repo_url}\nspecs\ndownloaded\n",
    )

    assert result.exit_code == 0, result.output
    config_path = tmp_path / ".swax" / "config.yml"
    assert config_path.exists()
    assert (tmp_path / "downloaded" / "api.yaml").exists()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["git"]["url"] == repo_url
    assert config["git"]["location"] == "specs"
    assert config["specs"]["type"] == "openapi"
    assert config["specs"]["location"] == "downloaded"


def test_swax_discover_end_to_end_with_mocked_llm(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    swax_dir = tmp_path / ".swax"
    swax_dir.mkdir()
    (swax_dir / "config.yml").write_text(
        "git:\n  url: https://example.com/repo.git\n  location: specs/\nspecs:\n  type: openapi\n  location: specs\n",
        encoding="utf-8",
    )
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "api.yaml").write_text(OPENAPI_SPEC, encoding="utf-8")

    _wire_llm_mock(mocker.patch(BUILD_CLIENT))

    result = CliRunner().invoke(main, ["--env-file", str(tmp_path / ".env"), "discover"])

    assert result.exit_code == 0, result.output
    trace_path = tmp_path / ".swax" / "traceability.yml"
    assert trace_path.exists()
    data = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
    assert data == EXPECTED_GRAPH


def test_swax_full_pipeline_init_then_discover(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    repo_url = _make_remote_repo(tmp_path / "remote")

    _wire_llm_mock(mocker.patch(BUILD_CLIENT))
    runner = CliRunner()

    init_result = runner.invoke(
        main,
        ["--env-file", str(tmp_path / ".env"), "init"],
        input=f"{repo_url}\nspecs\ndownloaded\n",
    )
    assert init_result.exit_code == 0, init_result.output
    assert (tmp_path / ".swax" / "config.yml").exists()
    assert (tmp_path / "downloaded" / "api.yaml").exists()

    discover_result = runner.invoke(main, ["--env-file", str(tmp_path / ".env"), "discover"])

    assert discover_result.exit_code == 0, discover_result.output
    trace_path = tmp_path / ".swax" / "traceability.yml"
    assert trace_path.exists()
    data = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
    assert data == EXPECTED_GRAPH
