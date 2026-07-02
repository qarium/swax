"""Application use-case cell for the traceability graph rebuild.

The facade re-exports run_discover, the two-pass LLM use-case that orchestrates
config loading, spec discovery/parsing, LLM dependency analysis (initial + refine
pass), and graph persistence across the config, openapi, llm, prompts, and
traceability cells. This cell contains no business logic beyond sequencing and
defensive response parsing.
"""

from .run_discover import run_discover

__all__: list[str] = ["run_discover"]
