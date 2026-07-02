"""First-pass user prompt for dependency hypotheses.

build_graph_user_prompt renders the endpoint list as JSON and instructs the LLM
to return a JSON object with exactly two keys — dependencies and uncertain —
matching what the consumer's first-pass parser expects.
"""

import json


def build_graph_user_prompt(endpoints: list[str]) -> str:
    """Build the first-pass user prompt listing API endpoints.

    Args:
        endpoints: API path templates collected by extract_paths across all
            parsed specs, in sorted order for determinism.

    Returns:
        The user message for the initial LLMClient.ask call.
    """
    payload = json.dumps({"endpoints": endpoints})

    return f"""Given these API endpoints:

{payload}

Return a JSON object with exactly two keys:
- "dependencies": object mapping source_path to list of dependent_paths
- "uncertain": list of uncertain dependency pairs as "/source -> /target" strings

The "uncertain" pairs will be refined in a follow-up turn with schema context."""


__all__: list[str] = [
    "build_graph_user_prompt",
]
