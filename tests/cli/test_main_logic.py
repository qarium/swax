"""Logic tests for the swax.cli cell (task 22).

The ``main`` group loads the environment, builds a ``SwaxContext`` on
``ctx.obj``, and stays silent on a missing env file. Subcommand registration is
lazy (``swax.cli.__main__``). The group callback only runs when a subcommand is
invoked (``--help`` short-circuits it), so a throwaway ``probe`` command is
registered on ``main`` to force the callback — letting ``load_env`` side effects
and ``ctx.obj`` be observed without coupling to the init/discover handlers.
"""

import os
import pathlib
import sys

import click
import pytest
import swax.cli.__main__  # noqa: F401  -- import side effect registers init/discover lazily
from click.testing import CliRunner
from swax.cli import SwaxContext, main

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # backport for Python 3.10


@pytest.fixture
def probe():
    """Register a no-op probe command on ``main`` and yield a capture holder.

    The probe forces the group callback (``load_env`` + ``ctx.obj`` assignment)
    by being invoked as a subcommand, then unregisters itself so the global
    ``main`` group stays clean for other tests.
    """
    captured: dict[str, object] = {}

    @click.command()
    @click.pass_obj
    def _probe(obj: object) -> None:
        captured["obj"] = obj

    main.add_command(_probe, name="probe")
    try:
        yield captured
    finally:
        main.commands.pop("probe", None)


def test_main_loads_env_file_when_exists(tmp_path, monkeypatch, probe):
    env_file = tmp_path / ".env"
    env_file.write_text("SWAX_LLM_TOKEN=fromfile\n", encoding="utf-8")
    monkeypatch.delenv("SWAX_LLM_TOKEN", raising=False)

    result = CliRunner().invoke(main, ["--env-file", str(env_file), "probe"])

    assert result.exit_code == 0
    assert os.environ["SWAX_LLM_TOKEN"] == "fromfile"


def test_main_silent_on_missing_env_file(tmp_path, probe):
    missing = tmp_path / "does-not-exist.env"

    result = CliRunner().invoke(main, ["--env-file", str(missing), "probe"])

    assert result.exit_code == 0


def test_main_sets_swax_context_with_env_file(probe):
    result = CliRunner().invoke(main, ["--env-file", "custom.env", "probe"])

    assert result.exit_code == 0
    assert isinstance(probe["obj"], SwaxContext)
    assert probe["obj"].env_file == pathlib.Path("custom.env")


def test_main_registers_init_and_discover_lazily():
    assert "init" in main.commands
    assert "discover" in main.commands


def test_main_registers_update_command():
    assert "update" in main.commands
    assert main.commands["update"].name == "update"


def test_swax_context_default_config_is_none():
    assert SwaxContext(env_file=pathlib.Path(".env")).config is None


def test_entry_point_registered():
    pyproject = pathlib.Path("pyproject.toml")
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["scripts"]["swax"] == "swax.cli.__main__:main"
