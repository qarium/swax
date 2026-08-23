"""User prompt for the incremental dependency graph revision.

build_incremental_graph_user_prompt renders the revision input of run_update:
the current graph, the endpoint-level changes of the modified spec files, the
endpoints and schemas of the newly added spec files, and the computed endpoint
universe. The caller supplies sorted structures; this routine renders them in
insertion order and never truncates silently.
"""

import json


# The six-argument shape is pinned by the CODEMANIFEST contract — the revision
# input is exactly these primitives, so the argument count cannot be reduced.
def build_incremental_graph_user_prompt(  # noqa: PLR0913, PLR0917
    existing_edges: dict[str, list[str]],
    diff_added: list[str],
    diff_removed: list[str],
    diff_modified: dict[str, list[str]],
    added_endpoints: list[str],
    added_schemas: dict,
) -> str:
    """Build the user prompt carrying the revision input for run_update.

    Args:
        existing_edges: the current graph as source path -> dependent paths.
        diff_added: endpoint paths added by the modified spec files.
        diff_removed: endpoint paths removed by the modified spec files.
        diff_modified: endpoint path mapped to a list of human-readable change
            descriptions.
        added_endpoints: endpoints extracted from the newly added spec files.
        added_schemas: schema definitions from the newly added spec files,
            attached as context.

    Returns:
        The user message for the single-turn LLMClient.ask call in run_update.
    """
    graph_payload = json.dumps(existing_edges)
    changes_payload = json.dumps({"added": diff_added, "removed": diff_removed, "modified": diff_modified})
    # default=str: parsed YAML carries non-JSON-native scalars (unquoted dates
    # become datetime.date), which would otherwise raise mid-rebuild.
    new_specs_payload = json.dumps({"endpoints": added_endpoints, "schemas": added_schemas}, default=str)

    universe = sorted((set(existing_edges) - set(diff_removed)) | set(diff_added) | set(added_endpoints))

    return (
        "Revise the existing dependency graph given the changes below.\n"
        "\n"
        f"Current graph (source_path -> dependent_paths):\n{graph_payload}\n"
        "\n"
        f"Endpoint changes in modified specifications:\n{changes_payload}\n"
        "\n"
        f"Newly added specifications (endpoints and schema definitions):\n"
        f"{new_specs_payload}\n"
        "\n"
        f"The complete endpoint universe after the update:\n{json.dumps(universe)}\n"
        "\n"
        "Return the complete updated dependency mapping covering exactly every "
        "endpoint of the universe above."
    )


__all__: list[str] = [
    "build_incremental_graph_user_prompt",
]
