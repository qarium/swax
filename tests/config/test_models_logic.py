"""Logic tests for the swax.config pydantic models.

Covers validation behavior: dict round-trip, Literal enforcement on
SpecsConfig.type, and the absence of URL validation on GitConfig.
"""

import pytest
from pydantic import ValidationError
from swax.config import Config, GitConfig, SpecsConfig


class TestModelsLogic:
    def test_config_validates_from_dict(self):
        raw = {
            "git": {"url": "https://example.com/repo.git", "location": "specs"},
            "specs": {"type": "openapi", "location": "local_specs"},
        }

        config = Config.model_validate(raw)

        assert config.git.url == "https://example.com/repo.git"
        assert config.git.location == "specs"
        assert config.specs.type == "openapi"
        assert config.specs.location == "local_specs"

    def test_specsconfig_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            SpecsConfig(type="invalid", location="loc")

    def test_gitconfig_accepts_arbitrary_strings(self):
        git = GitConfig(url="not-a-real-url", location="any/where")

        assert git.url == "not-a-real-url"
        assert git.location == "any/where"

    @pytest.mark.parametrize("spec_type", ["swagger", "openapi"])
    def test_specsconfig_accepts_supported_types(self, spec_type):
        specs = SpecsConfig(type=spec_type, location="loc")

        assert specs.type == spec_type
