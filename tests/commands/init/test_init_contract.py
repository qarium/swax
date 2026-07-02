"""Contract tests for the swax.commands.init cell (task 19).

These tests pin the public surface: the Click command `init` must be importable
from the facade and be a registered click.Command. They fail with ImportError or
AttributeError until the cell exposes `init`.
"""

import click
import swax.commands.init as init_cell
from swax.commands.init import init


class TestInitContract:
    def test_init_is_importable_from_facade(self):
        assert callable(init)

    def test_init_is_a_click_command(self):
        assert isinstance(init, click.Command)

    def test_init_callback_is_attached(self):
        assert init.callback is not None


class TestFacadeExposure:
    def test_facade_all_contains_only_init(self):
        assert init_cell.__all__ == ["init"]
