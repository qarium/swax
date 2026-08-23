"""SpecsChanges pydantic value object."""

from pydantic import BaseModel, ConfigDict, Field


class SpecsChanges(BaseModel):
    """File-level classification of specification changes between the local specs directory and the remote clone.

    Args:
        added: relative file paths present only in the remote state.
        updated: relative file paths present in both states with differing bytes.
        removed: relative file paths present only in the local state.
    """

    model_config = ConfigDict(kw_only=True)

    added: list[str] = Field(default_factory=list)
    updated: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)

    def has_changes(self) -> bool:
        """Report whether any list is non-empty.

        Returns:
            changed: True when at least one of added, updated, removed is non-empty.
        """
        return bool(self.added or self.updated or self.removed)

    def has_additions(self) -> bool:
        """Report whether the change set requires content parsing.

        Returns:
            present: True when the added or updated list is non-empty — drives
                the LLM-requiring branch.
        """
        return bool(self.added or self.updated)


__all__: list[str] = [
    "SpecsChanges",
]
