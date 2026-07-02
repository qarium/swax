"""Contract tests for the swax.applications.discover cell (task 17).

These tests pin the public surface: run_discover must be importable from the
facade with the documented single-parameter signature (project_root). They fail
with ImportError until the facade re-exports run_discover.
"""

import inspect
import pathlib

import swax.applications.discover as discover_cell
from swax.applications.discover import run_discover


class TestRunDiscoverContract:
    def test_run_discover_is_importable_from_facade(self):
        assert callable(run_discover)

    def test_run_discover_has_documented_signature(self):
        params = list(inspect.signature(run_discover).parameters)

        assert params == ["project_root"]

    def test_run_discover_project_root_typed_as_pathlib(self):
        annotations = inspect.signature(run_discover).parameters

        assert annotations["project_root"].annotation is pathlib.Path

    def test_run_discover_returns_none(self):
        assert inspect.signature(run_discover).return_annotation is None


class TestFacadeExposure:
    def test_facade_all_contains_only_run_discover(self):
        assert discover_cell.__all__ == ["run_discover"]
