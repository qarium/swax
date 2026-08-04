"""EndpointDiff pydantic entity.

Classified change result between a baseline and a current specification:
endpoints added, removed, or modified (the latter keyed by path to a list of
human-readable change descriptions). The model is produced by
classify_endpoint_changes and consumed by run_plan for the no-change
short-circuit (has_changes) and the affected-endpoints computation
(changed_paths).
"""

from pydantic import BaseModel, ConfigDict, Field


class EndpointDiff(BaseModel):
    """Classified endpoint changes between baseline and current specs.

    Args:
        added: endpoint paths present in the current spec but not in the
            baseline. Defaults to empty.
        removed: endpoint paths present in the baseline but not in the current
            spec. Defaults to empty.
        modified: endpoint path mapped to its list of human-readable change
            descriptions. Defaults to empty.
    """

    model_config = ConfigDict(kw_only=True)

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: dict[str, list[str]] = Field(default_factory=dict)

    def has_changes(self) -> bool:
        """Return True when any endpoint was added, removed, or modified.

        Returns:
            True if at least one of the three buckets is non-empty.
        """
        return bool(self.added or self.removed or self.modified)

    def changed_paths(self) -> list[str]:
        """Return the union of added, removed, and modified endpoint paths.

        The union is sorted and deduplicated — each path appears once even when
        it is present in more than one bucket.

        Returns:
            Sorted, deduplicated list of all changed endpoint paths.
        """
        return sorted(set(self.added) | set(self.removed) | set(self.modified.keys()))


__all__: list[str] = [
    "EndpointDiff",
]
