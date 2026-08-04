"""ImpactReport pydantic entity.

Structured representation of the LLM-produced (or the no-change placeholder)
Impact Report. It is the defensive-parse target of run_plan and the sole input
to render_impact_report. The six fields map one-to-one onto the JSON contract
exposed by the impact-report system prompt; risk is constrained to
{HIGH, MEDIUM, LOW} by run_plan (this model does not validate it).
"""

from pydantic import BaseModel, ConfigDict, Field


class ImpactReport(BaseModel):
    """Structured Impact Report produced by the LLM analysis.

    Args:
        summary: one-line human-readable summary of the change impact.
        risk: overall risk level — HIGH, MEDIUM, or LOW (validated by
            run_plan; the model itself does not constrain the value).
        modified: endpoint paths that changed.
        affected: endpoint paths transitively affected via the graph.
        requirements: testing requirements derived from the changes.
        checklist: actionable verification checklist items.
    """

    model_config = ConfigDict(kw_only=True)

    summary: str
    risk: str
    modified: list[str] = Field(default_factory=list)
    affected: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)


__all__: list[str] = [
    "ImpactReport",
]
