"""Application use-case cell for change-impact analysis.

The facade will re-export run_plan, the single-turn LLM use-case that diffs
baseline vs fresh specs, maps changes onto the traceability graph, and renders a
Markdown Impact Report across the config, git, openapi, traceability, prompts,
and llm cells. run_plan is added to this facade in a follow-up task; the
ImpactReport model and the render_impact_report transform are already
available as submodules.
"""

__all__: list[str] = []
