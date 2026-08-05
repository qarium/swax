"""Application use-case cell for change-impact analysis.

The facade re-exports run_plan, the single-turn LLM use-case that diffs baseline
vs fresh specs, maps changes onto the traceability graph, and renders a Markdown
Impact Report across the config, git, openapi, traceability, prompts, and llm
cells. This cell contains no business logic beyond sequencing, defensive
response parsing, and the MEDIUM risk fallback.
"""

from .run_plan import run_plan

__all__: list[str] = ["run_plan"]
