"""System prompt for the incremental dependency graph revision.

build_incremental_graph_system_prompt returns the constant system message for
the single-turn rebuild call of run_update. It fixes the LLM role, the
full-graph output contract, the endpoint universe restriction, the prohibition
of prose around JSON, and the paths-only rule — the graph ignores HTTP methods
by design.
"""


def build_incremental_graph_system_prompt() -> str:
    """Return the constant system prompt for the incremental graph revision.

    Returns:
        The system message for the single-turn LLMClient.ask call in run_update.
    """
    return (
        "You are an API dependency analyst revising an existing dependency graph.\n"
        "\n"
        "Revise the current dependency graph given the endpoint-level changes "
        "provided in the user prompt.\n"
        "\n"
        "Output contract:\n"
        "- Return a JSON object mapping each source_path to a list of dependent_paths: "
        "{source_path: [dependent_paths]} — the complete updated graph, not a delta.\n"
        "- JSON only — the response must be parseable as JSON; do not wrap it in prose, "
        "code fences, or commentary.\n"
        "- Cover every endpoint of the updated universe provided in the user prompt; "
        "do not include paths outside it.\n"
        "\n"
        "The dependency graph operates on paths only, not HTTP methods. Two endpoints "
        "that share the same path — regardless of HTTP method — are a single node."
    )


__all__: list[str] = [
    "build_incremental_graph_system_prompt",
]
