"""Contract tests for the swax.fs cell.

These tests pin the public surface and signatures of ensure_swax_dir and
copy_specs. They fail with ImportError until the routines and the facade
re-exports exist (task 7).
"""

import inspect
import pathlib

from swax.fs import copy_specs, ensure_swax_dir


class TestFsContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(ensure_swax_dir)
        assert callable(copy_specs)

    def test_ensure_swax_dir_signature(self):
        signature = inspect.signature(ensure_swax_dir)

        assert list(signature.parameters) == ["project_root"]
        assert signature.parameters["project_root"].annotation is pathlib.Path
        assert signature.return_annotation is pathlib.Path

    def test_copy_specs_signature(self):
        signature = inspect.signature(copy_specs)

        assert list(signature.parameters) == ["source", "destination"]
        assert signature.parameters["source"].annotation is pathlib.Path
        assert signature.parameters["destination"].annotation is pathlib.Path
