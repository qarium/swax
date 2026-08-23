"""Refine-pass user prompt for ambiguous dependency pairs.

build_refine_user_prompt renders the uncertain pairs flagged in the first pass
together with the schema definitions, and asks the LLM for a consolidated
decision without introducing paths outside the endpoint universe. The output
contract matches build_graph_user_prompt so the consumer reuses the same parser.
"""

import json


def build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> str:
    """Build the refine-pass user prompt with ambiguous pairs and schemas.

    Args:
        ambiguous_pairs: pairs flagged as uncertain in the first-pass response
            (e.g. "/users -> /orders").
        schemas: schema definitions from extract_schemas, attached as context.

    Returns:
        The user message for the final turn of LLMClient.ask_multi_turn.
    """
    pairs_payload = json.dumps({"ambiguous_pairs": ambiguous_pairs})
    # default=str: parsed YAML carries non-JSON-native scalars (unquoted dates
    # become datetime.date), which would otherwise raise mid-rebuild.
    schemas_payload = json.dumps({"schemas": schemas}, default=str)

    return f"""Refine these ambiguous dependency pairs using schemas:

{pairs_payload}

{schemas_payload}

Return consolidated JSON object {{source_path: [dependent_paths]}}.
Do not introduce paths outside the provided endpoint universe."""


__all__: list[str] = [
    "build_refine_user_prompt",
]
