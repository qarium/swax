"""LLM prompt builders for the traceability graph construction.

The facade re-exports the seven prompt-builder routines: three for the
two-pass discover scenario, two for the single-turn impact-report scenario,
and two for the single-turn incremental rebuild of the update scenario. Every
routine returns a fully-formed prompt string ready for LLMClient.ask /
ask_multi_turn. Prompts request structured JSON output and never embed
filesystem paths, tokens, or secrets — only the data passed as arguments.
"""

from .build_graph_system_prompt import build_graph_system_prompt
from .build_graph_user_prompt import build_graph_user_prompt
from .build_impact_report_system_prompt import build_impact_report_system_prompt
from .build_impact_report_user_prompt import build_impact_report_user_prompt
from .build_incremental_graph_system_prompt import build_incremental_graph_system_prompt
from .build_incremental_graph_user_prompt import build_incremental_graph_user_prompt
from .build_refine_user_prompt import build_refine_user_prompt

__all__: list[str] = [
    "build_graph_system_prompt",
    "build_graph_user_prompt",
    "build_impact_report_system_prompt",
    "build_impact_report_user_prompt",
    "build_incremental_graph_system_prompt",
    "build_incremental_graph_user_prompt",
    "build_refine_user_prompt",
]
