"""Config pydantic model."""

from pydantic import BaseModel, ConfigDict

from .GitConfig import GitConfig
from .SpecsConfig import SpecsConfig


class Config(BaseModel):
    """Root configuration model of a Swax project, persisted to .swax/config.yml.

    Args:
        git: git repository coordinates for the source specifications.
        specs: local layout of downloaded specifications.
    """

    model_config = ConfigDict(kw_only=True)

    git: GitConfig
    specs: SpecsConfig
