"""Contract tests for the swax.config storage routines.

These tests pin the public surface and signatures of load_config and
save_config. They fail with ImportError until the routines and their facade
re-exports exist (task 5).
"""

import inspect
import pathlib

from swax.config import Config, load_config, save_config


class TestStorageContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(load_config)
        assert callable(save_config)

    def test_load_config_signature(self):
        signature = inspect.signature(load_config)

        assert list(signature.parameters) == ["path"]
        assert signature.parameters["path"].annotation is pathlib.Path
        assert signature.return_annotation is Config

    def test_save_config_signature(self):
        signature = inspect.signature(save_config)

        assert list(signature.parameters) == ["config", "path"]
        assert signature.parameters["config"].annotation is Config
        assert signature.parameters["path"].annotation is pathlib.Path
