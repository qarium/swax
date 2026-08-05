"""Contract tests for run_plan (task 6).

These tests pin the public surface: run_plan is importable from the plan facade
with the documented signature (project_root: pathlib.Path) -> str. They fail
with ImportError until the facade re-exports run_plan.
"""

import inspect
import pathlib

import swax.applications.plan as plan_cell
from swax.applications.plan import run_plan


class TestRunPlanContract:
    def test_run_plan_is_importable_from_facade(self):
        assert callable(run_plan)

    def test_run_plan_has_documented_signature(self):
        params = list(inspect.signature(run_plan).parameters)

        assert params == ["project_root"]

    def test_run_plan_project_root_typed_as_pathlib(self):
        annotations = inspect.signature(run_plan).parameters

        assert annotations["project_root"].annotation is pathlib.Path

    def test_run_plan_returns_str(self):
        assert inspect.signature(run_plan).return_annotation is str


class TestFacadeExposure:
    def test_facade_all_contains_only_run_plan(self):
        assert plan_cell.__all__ == ["run_plan"]
