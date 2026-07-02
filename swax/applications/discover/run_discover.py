"""Application use-case: rebuild the traceability graph (two-pass LLM analysis).

run_discover performs a full, from-scratch rebuild of the traceability graph
across five domain cells (config, openapi, llm, prompts, traceability). It
validates LLM credentials, reads the project Config, discovers and parses the
local spec files to collect endpoints and schema context, then runs two LLM
passes: an initial dependency-graph pass and a refine pass that resolves the
uncertain pairs flagged in the first pass using schema context. The final
dependencies are loaded into a TraceabilityGraph, deduplicated, and persisted to
.swax/traceability.yml, overwriting any prior graph.

LLM responses are parsed defensively: prose and code fences around the JSON are
stripped, JSONDecodeError is wrapped into LLMResponseParseError (with a raw
excerpt), and the parsed shape is validated as dict[str, list[str]]. The six
domain errors (MissingEnvironmentVariablesError, SpecParseError, LLMCallError,
LLMRateLimitedError, UnsupportedLLMProtocolError, LLMResponseParseError)
propagate uncaught — the CLI handler maps them to click.ClickException.
SWAX_LLM_TOKEN never appears in logs.
"""

import json
import logging
import pathlib

from swax.config import Config, load_config, require_vars
from swax.llm import LLMClient, LLMResponseParseError, build_llm_client
from swax.openapi import discover_specs, extract_paths, extract_schemas, parse_spec
from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
    build_refine_user_prompt,
)
from swax.traceability import TraceabilityGraph, save_traceability

logger = logging.getLogger(__name__)

_EXCERPT_LENGTH = 200


def _strip_prose_and_fences(raw: str) -> str:
    """Return the substring spanning the first ``{`` to the last ``}``.

    If the payload contains no balanced braces, it is returned unchanged so
    ``json.loads`` raises an informative error.
    """
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace == -1 or last_brace == -1 or first_brace > last_brace:
        return raw
    return raw[first_brace : last_brace + 1]


def _validate_dependency_shape(d: dict) -> None:
    """Assert ``d`` matches dict[str, list[str]] or raise LLMResponseParseError."""
    for key, value in d.items():
        if not isinstance(key, str) or not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LLMResponseParseError(
                reason="shape mismatch: expected dict[str, list[str]]",
                excerpt=str(d)[:_EXCERPT_LENGTH],
            )


def _parse_llm_json(raw: str, *, first_pass: bool) -> tuple[dict[str, list[str]], list[str]]:
    """Defensively parse an LLM response into dependencies (and uncertain pairs).

    Args:
        raw: raw model output, possibly wrapped in prose or code fences.
        first_pass: when True the expected shape is
            ``{"dependencies": dict[str, list[str]], "uncertain": list[str]}``;
            when False the expected shape is a flat ``dict[str, list[str]]``.

    Returns:
        A ``(dependencies, uncertain)`` tuple. ``uncertain`` is always empty
        after the refine pass.

    Raises:
        LLMResponseParseError: when the payload is not valid JSON, not a dict,
            has the wrong keys (first pass), or fails the shape validation.
    """
    stripped = _strip_prose_and_fences(raw)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMResponseParseError(reason=str(exc), excerpt=stripped[:_EXCERPT_LENGTH]) from exc
    if not isinstance(parsed, dict):
        raise LLMResponseParseError(reason="not a dict", excerpt=stripped[:_EXCERPT_LENGTH])
    if first_pass:
        if set(parsed.keys()) != {"dependencies", "uncertain"}:
            raise LLMResponseParseError(
                reason="first pass: keys must be dependencies+uncertain",
                excerpt=stripped[:_EXCERPT_LENGTH],
            )
        dependencies = parsed["dependencies"]
        uncertain = parsed["uncertain"]
        _validate_dependency_shape(dependencies)
        if not isinstance(uncertain, list) or not all(isinstance(item, str) for item in uncertain):
            raise LLMResponseParseError(
                reason="uncertain: must be list[str]",
                excerpt=stripped[:_EXCERPT_LENGTH],
            )
        return dependencies, uncertain
    _validate_dependency_shape(parsed)
    return parsed, []


def run_discover(project_root: pathlib.Path) -> None:
    """Rebuild the traceability graph via a two-pass LLM dependency analysis.

    Args:
        project_root: root of the Swax project. ``.swax/config.yml`` describes
            the local specs root; ``.swax/traceability.yml`` is overwritten with
            the freshly built graph.

    Raises:
        MissingEnvironmentVariablesError: when an LLM credential is missing
            (propagated from require_vars).
        SpecParseError: when a discovered spec cannot be parsed (propagated).
        UnsupportedLLMProtocolError: when SWAX_LLM_PROTOCOL is unknown
            (propagated from build_llm_client).
        LLMCallError: on a generic LLM API failure (propagated).
        LLMRateLimitedError: on an LLM rate-limit failure (propagated).
        LLMResponseParseError: when an LLM response cannot be parsed into the
            expected shape (propagated).
    """
    require_vars()
    logger.info("discover started", extra={"project_root": str(project_root)})

    config: Config = load_config(project_root / ".swax" / "config.yml")
    specs_root = project_root / config.specs.location
    spec_files = discover_specs(specs_root)

    endpoints: list[str] = []
    schemas: dict = {}
    for spec_path in spec_files:
        spec = parse_spec(spec_path)
        endpoints.extend(extract_paths(spec))
        schemas.update(extract_schemas(spec))

    client: LLMClient = build_llm_client()
    system = build_graph_system_prompt()
    first_user = build_graph_user_prompt(endpoints)
    raw_first = client.ask(system=system, user=first_user)
    # The first pass is parsed/validated for its uncertain pairs; its dependency
    # map is superseded by the consolidate result of the refine pass below.
    _first_dependencies, uncertain = _parse_llm_json(raw_first, first_pass=True)

    ambiguous_pairs = uncertain
    refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)
    raw_refined = client.ask_multi_turn(
        system=system,
        messages=[
            {"role": "user", "content": first_user},
            {"role": "assistant", "content": raw_first},
            {"role": "user", "content": refine_user},
        ],
    )
    final_dependencies, _ = _parse_llm_json(raw_refined, first_pass=False)

    graph = TraceabilityGraph(edges={})
    for source, targets in final_dependencies.items():
        for target in targets:
            graph.add_edge(source=source, target=target)
    graph.deduplicate()
    save_traceability(graph, project_root / ".swax" / "traceability.yml")

    logger.info(
        "discover completed",
        extra={
            "project_root": str(project_root),
            "edges_count": sum(len(value) for value in graph.edges.values()),
        },
    )


__all__: list[str] = ["run_discover"]
