"""Contract tests for the swax.commands.update cell.

These tests pin the public surface: the Click command `update` must be importable
from the facade (``swax.commands.update``) and be a registered ``click.Command``
whose callback is wired with ``@click.pass_obj``. They fail with ImportError or
AttributeError until the cell exposes ``update``.
"""

import click
import swax.commands.update as update_cell
from swax.commands.update import update


class TestUpdateContract:
    def test_update_is_importable_from_facade(self):
        assert callable(update)

    def test_update_is_a_click_command(self):
        assert isinstance(update, click.Command)

    def test_update_callback_is_attached(self):
        assert update.callback is not None

    def test_update_callback_is_decorated_with_pass_obj(self):
        """``@click.pass_obj`` wraps the callback with ``functools.wraps``."""
        assert hasattr(update.callback, "__wrapped__")
        assert update.callback.__wrapped__.__name__ == "update"

    def test_update_command_has_no_options(self):
        assert update.params == []


class TestFacadeExposure:
    def test_facade_all_contains_only_update(self):
        assert update_cell.__all__ == ["update"]
