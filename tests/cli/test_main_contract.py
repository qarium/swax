"""Contract tests for the swax.cli cell (task 22).

Pin the public surface: ``main`` and ``SwaxContext`` must be importable from the
facade, ``main`` must be a ``click.Group``, and ``SwaxContext`` must be a
kw_only pydantic model whose ``env_file`` and ``config`` attributes are
accessible (``config`` defaulting to ``None``). These fail with ImportError or
AttributeError until the cell exposes both names.
"""

import pathlib

import click
import pytest
from swax.cli import SwaxContext, __all__, main


def test_facade_exposes_main_and_swax_context() -> None:
    assert callable(main)
    assert SwaxContext is not None


def test_main_is_a_click_group() -> None:
    assert isinstance(main, click.Group)


def test_facade_all_lists_main_and_swax_context() -> None:
    assert __all__ == ["SwaxContext", "main"]


def test_swax_context_is_kw_only() -> None:
    """env_file must be supplied as a keyword argument (kw_only contract)."""
    with pytest.raises(TypeError):
        SwaxContext(pathlib.Path(".env"))  # type: ignore[misc]


def test_swax_context_exposes_env_file() -> None:
    ctx = SwaxContext(env_file=pathlib.Path(".env"))
    assert ctx.env_file == pathlib.Path(".env")


def test_swax_context_config_defaults_to_none() -> None:
    ctx = SwaxContext(env_file=pathlib.Path(".env"))
    assert ctx.config is None
