"""User prompt for the API change impact report scenario.

build_impact_report_user_prompt renders the five change-context primitives as
JSON and instructs the LLM to return the Impact Report JSON contract defined in
the system prompt. The caller (run_plan) trims large inputs before calling;
this routine never truncates silently.
"""

import json


def build_impact_report_user_prompt(
    added: list[str],
    removed: list[str],
    modified: dict[str, list[str]],
    affected: list[str],
    graph_context: dict[str, list[str]],
) -> str:
    """Build the user prompt carrying the change context for run_plan.

    Args:
        added: endpoint paths present in the fresh specs but absent in baseline.
        removed: endpoint paths present in baseline but absent in the fresh specs.
        modified: endpoint path mapped to a list of human-readable change
            descriptions.
        affected: transitively affected endpoint paths.
        graph_context: relevant graph edges (endpoint path -> dependency paths)
            sliced from the traceability graph for the affected paths.

    Returns:
        The user message for the single-turn LLMClient.ask call in run_plan.
    """
    added_json = json.dumps(added)
    removed_json = json.dumps(removed)
    modified_json = json.dumps(modified, sort_keys=True)
    affected_json = json.dumps(affected)
    graph_json = json.dumps(graph_context, sort_keys=True)

    return (
        "Assess the testing impact of the following API endpoint changes.\n"
        "\n"
        f"Added endpoints:\n{added_json}\n"
        "\n"
        f"Removed endpoints:\n{removed_json}\n"
        "\n"
        f"Modified endpoints:\n{modified_json}\n"
        "\n"
        f"Affected endpoints:\n{affected_json}\n"
        "\n"
        f"Graph context:\n{graph_json}\n"
        "\n"
        "Return the Impact Report JSON contract from the system prompt."
    )


__all__: list[str] = [
    "build_impact_report_user_prompt",
]
