"""Contract tests for the swax.config pydantic models.

These tests pin the public surface and the kw_only contract of Config,
GitConfig, and SpecsConfig. They fail with ImportError until the models and
their facade re-exports exist (task 2).
"""

import pytest
from swax.config import Config, GitConfig, SpecsConfig


class TestModelsContract:
    def test_models_are_importable_from_facade(self):
        assert Config is not None
        assert GitConfig is not None
        assert SpecsConfig is not None

    def test_gitconfig_requires_keyword_args(self):
        with pytest.raises(TypeError):
            GitConfig("https://example.com/repo.git", "specs")

    def test_specsconfig_requires_keyword_args(self):
        with pytest.raises(TypeError):
            SpecsConfig("openapi", "local_specs")

    def test_config_requires_keyword_args(self):
        git = GitConfig(url="https://example.com/repo.git", location="specs")
        specs = SpecsConfig(type="openapi", location="local_specs")

        with pytest.raises(TypeError):
            Config(git, specs)

    def test_config_round_trips_through_model_dump(self):
        git = GitConfig(url="https://example.com/repo.git", location="specs")
        specs = SpecsConfig(type="openapi", location="local_specs")
        config = Config(git=git, specs=specs)

        dumped = config.model_dump()

        assert dumped == {
            "git": {"url": "https://example.com/repo.git", "location": "specs"},
            "specs": {"type": "openapi", "location": "local_specs"},
        }

        rebuilt = Config.model_validate(dumped)
        assert rebuilt == config
