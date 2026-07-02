"""System prompt for the API dependency analyst role.

build_graph_system_prompt returns the constant system message reused across
both passes of run_discover. It fixes the LLM role, the JSON output contract,
the prohibition of prose around JSON, and the paths-only rule — the graph
ignores HTTP methods by design.
"""


def build_graph_system_prompt() -> str:
    """Return the constant system prompt for the dependency analyst.

    Returns:
        The system message reused across both LLM passes of run_discover.
    """
    return (
        "You are an API dependency analyst.\n"
        "\n"
        "Analyze the provided API endpoints and propose dependency edges between them.\n"
        "\n"
        "Output contract:\n"
        "- Return a JSON object mapping each source_path to a list of dependent_paths: "
        "{source_path: [dependent_paths]}.\n"
        "- JSON only — do not wrap the response in prose, code fences, or commentary. "
        "The response must be parseable as JSON.\n"
        "\n"
        "The dependency graph operates on paths only, not HTTP methods. Two endpoints "
        "that share the same path — regardless of HTTP method — are a single node."
    )


__all__: list[str] = [
    "build_graph_system_prompt",
]
