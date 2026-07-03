"""SpecsConfig pydantic model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SpecsConfig(BaseModel):
    """Local layout of downloaded specifications.

    Args:
        type: declared spec format (swagger or openapi). Informational only —
            the parser detects the actual version at parse time.
        location: local path where copy_specs writes specs.
    """

    model_config = ConfigDict(kw_only=True)

    type: Literal["swagger", "openapi"]
    location: str
