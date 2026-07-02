"""Contract tests for the swax.applications.init cell (task 16).

These tests pin the public surface: run_init must be importable from the
facade with the documented four-parameter signature (repo_url, specs_location,
download_path, project_root). They fail with ImportError until the facade
re-exports run_init.
"""

import inspect
import pathlib

import swax.applications.init as init_cell
from swax.applications.init import run_init


class TestRunInitContract:
    def test_run_init_is_importable_from_facade(self):
        assert callable(run_init)

    def test_run_init_has_documented_signature(self):
        params = list(inspect.signature(run_init).parameters)

        assert params == ["repo_url", "specs_location", "download_path", "project_root"]

    def test_run_init_path_arguments_typed_as_pathlib(self):
        annotations = inspect.signature(run_init).parameters

        assert annotations["download_path"].annotation is pathlib.Path
        assert annotations["project_root"].annotation is pathlib.Path

    def test_run_init_returns_none(self):
        assert inspect.signature(run_init).return_annotation is None


class TestFacadeExposure:
    def test_facade_all_contains_only_run_init(self):
        assert init_cell.__all__ == ["run_init"]
