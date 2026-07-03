"""GitConfig pydantic model."""

from pydantic import BaseModel, ConfigDict


class GitConfig(BaseModel):
    """Coordinates of the remote git repository holding API specifications.

    Args:
        url: clone URL consumed by clone_specs.
        location: subdirectory inside the repository where specs live.
    """

    model_config = ConfigDict(kw_only=True)

    url: str
    location: str
