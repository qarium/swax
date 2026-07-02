"""Contract tests for the swax.commands.discover cell (task 20).

These tests pin the public surface: the Click command `discover` must be
importable from the facade and be a registered click.Command. They fail with
ImportError or AttributeError until the cell exposes `discover`.
"""

import click
import swax.commands.discover as discover_cell
from swax.commands.discover import discover


class TestDiscoverContract:
    def test_discover_is_importable_from_facade(self):
        assert callable(discover)

    def test_discover_is_a_click_command(self):
        assert isinstance(discover, click.Command)

    def test_discover_callback_is_attached(self):
        assert discover.callback is not None


class TestFacadeExposure:
    def test_facade_all_contains_only_discover(self):
        assert discover_cell.__all__ == ["discover"]
