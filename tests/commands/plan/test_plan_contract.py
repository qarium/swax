"""Contract tests for the swax.commands.plan cell.

These tests pin the public surface: the Click command `plan` must be importable
from the facade (``swax.commands.plan``) and be a registered ``click.Command``
whose callback is wired with ``@click.pass_obj``. They fail with ImportError or
AttributeError until the cell exposes ``plan``.
"""

import click
import swax.commands.plan as plan_cell
from swax.commands.plan import plan


class TestPlanContract:
    def test_plan_is_importable_from_facade(self):
        assert callable(plan)

    def test_plan_is_a_click_command(self):
        assert isinstance(plan, click.Command)

    def test_plan_callback_is_attached(self):
        assert plan.callback is not None

    def test_plan_callback_is_decorated_with_pass_obj(self):
        """``@click.pass_obj`` wraps the callback with ``functools.wraps``."""
        assert hasattr(plan.callback, "__wrapped__")
        assert plan.callback.__wrapped__.__name__ == "plan"


class TestFacadeExposure:
    def test_facade_all_contains_only_plan(self):
        assert plan_cell.__all__ == ["plan"]
