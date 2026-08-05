"""Application use-case: change-impact analysis (single-turn LLM scenario).

run_plan diffs the local baseline specs against a fresh clone of the specs
repository, maps the changed endpoints onto the traceability graph to find
transitively affected endpoints, and asks the LLM (single turn) to assess the
testing impact. The LLM response is parsed defensively into an ImpactReport and
rendered to Markdown.

It mirrors run_discover: require_vars up front, defensive JSON parsing with a
first-``{``-to-last-``}`` slice, JSONDecodeError wrapped into
LLMResponseParseError (with a raw excerpt), and the parsed shape validated
against the six-key ImpactReport contract. risk is coerced to upper and falls
back to MEDIUM when the model returns a value outside {HIGH, MEDIUM, LOW}.
Large affected sets are trimmed to _MAX_AFFECTED (changed-first, then sorted
remainder) before the prompt is built; both the prompt's affected array and the
graph_context are bounded by the kept set.

run_plan is the sole raiser of TraceabilityGraphMissingError (existence check
before load_traceability, which would otherwise silently yield an empty graph)
and LLMResponseParseError (defensive parse). The nine domain errors
(MissingEnvironmentVariablesError, SpecParseError, LLMCallError,
LLMRateLimitedError, UnsupportedLLMProtocolError, LLMResponseParseError,
RepositoryCloneError, SpecsNotFoundError, TraceabilityGraphMissingError)
propagate uncaught — the CLI handler maps them to click.ClickException.
SWAX_LLM_TOKEN never appears in logs or in the returned Markdown.
"""

import json
import logging
import pathlib

from ...config import Config, load_config, require_vars
from ...git import clone_specs
from ...llm import LLMClient, LLMResponseParseError, build_llm_client
from ...openapi import (
    EndpointDiff,
    classify_endpoint_changes,
    diff_specs,
    discover_specs,
    parse_spec,
)
from ...prompts import (
    build_impact_report_system_prompt,
    build_impact_report_user_prompt,
)
from ...traceability import (
    TraceabilityGraph,
    TraceabilityGraphMissingError,
    find_affected_endpoints,
    load_traceability,
)
from .impact_report import ImpactReport
from .render_impact_report import render_impact_report

logger = logging.getLogger(__name__)

_EXCERPT_LENGTH = 200
_MAX_AFFECTED = 100

_VALID_RISK = {"HIGH", "MEDIUM", "LOW"}
_REPORT_KEYS = {"summary", "risk", "modified", "affected", "requirements", "checklist"}


def _strip_prose_and_fences(raw: str) -> str:
    """Return the substring spanning the first ``{`` to the last ``}``.

    If the payload contains no balanced braces, it is returned unchanged so
    ``json.loads`` raises an informative error. Mirrors the convention used in
    run_discover's defensive parser.
    """
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace > last_brace:
        return raw

    return raw[first_brace : last_brace + 1]


def _parse_spec_map(
    paths: list[pathlib.Path],
    root: pathlib.Path,
) -> dict[str, dict]:
    """Parse each spec path into a dict keyed by its POSIX path relative to root.

    The matching key is the POSIX relative path so the same spec under baseline
    and the fresh clone align across the two maps.

    Args:
        paths: discovered spec file paths.
        root: directory the paths are relative to.

    Returns:
        Mapping of POSIX relative path to the parsed (dereferenced) spec dict.

    Raises:
        SpecParseError: when parse_spec fails on a candidate (propagated).
    """
    return {path.relative_to(root).as_posix(): parse_spec(path) for path in paths}


def _diff_and_classify(
    baseline: dict[str, dict],
    fresh: dict[str, dict],
) -> EndpointDiff:
    """Aggregate endpoint-level changes across matching spec pairs.

    For each relative path in the union of keys:
    - both sides: classify the per-spec diff and merge added/removed/modified;
    - fresh-only: the whole spec was added -> read its ``paths`` directly
      (diffing against ``{}`` would only surface the top-level ``paths`` key);
    - baseline-only: the whole spec was removed -> read its ``paths`` directly.

    Added/removed/modified are deduplicated (sets) and sorted for determinism.

    Args:
        baseline: parsed baseline specs keyed by POSIX relative path.
        fresh: parsed fresh (cloned) specs keyed by POSIX relative path.

    Returns:
        A single EndpointDiff aggregating every spec pair.
    """
    added: set[str] = set()
    removed: set[str] = set()
    modified: dict[str, set[str]] = {}

    for rel in sorted(set(baseline) | set(fresh)):
        if rel not in fresh:
            removed.update(baseline[rel].get("paths", {}).keys())
            continue
        if rel not in baseline:
            added.update(fresh[rel].get("paths", {}).keys())
            continue

        pair = classify_endpoint_changes(diff_specs(baseline[rel], fresh[rel]))
        added.update(pair.added)
        removed.update(pair.removed)
        for endpoint, descriptions in pair.modified.items():
            modified.setdefault(endpoint, set()).update(descriptions)

    return EndpointDiff(
        added=sorted(added),
        removed=sorted(removed),
        modified={endpoint: sorted(descriptions) for endpoint, descriptions in sorted(modified.items())},
    )


def _build_graph_context(
    affected: list[str],
    changed: list[str],
    graph: TraceabilityGraph,
) -> tuple[dict[str, list[str]], list[str]]:
    """Slice the graph edges for the (possibly trimmed) affected set.

    When the affected set exceeds ``_MAX_AFFECTED``, keep the changed paths
    first (in their existing order) then the sorted remainder, truncated to the
    cap, and log a WARNING. Both the returned graph_context and the trimmed
    affected list are bounded by the kept set.

    Args:
        affected: full reverse-reachable affected endpoint set.
        changed: the directly changed endpoints (kept first when trimming).
        graph: the read-only traceability graph.

    Returns:
        A ``(graph_context, trimmed_affected)`` tuple.
    """
    if len(affected) <= _MAX_AFFECTED:
        kept = affected
    else:
        affected_set = set(affected)
        kept_changed = [path for path in changed if path in affected_set]
        kept_changed_set = set(kept_changed)
        remainder = sorted(path for path in affected if path not in kept_changed_set)
        kept = (kept_changed + remainder)[:_MAX_AFFECTED]
        logger.warning(
            "plan context truncated",
            extra={"affected": len(affected), "kept": _MAX_AFFECTED},
        )

    graph_context = {path: list(graph.edges.get(path, [])) for path in kept}
    return graph_context, sorted(kept)


def _require_str(value: object, name: str, raw: str) -> None:
    """Raise LLMResponseParseError when value is not a str."""
    if not isinstance(value, str):
        raise LLMResponseParseError(
            reason=f"{name}: must be str",
            excerpt=raw[:_EXCERPT_LENGTH],
        )


def _require_str_list(value: object, name: str, raw: str) -> None:
    """Raise LLMResponseParseError when value is not a list[str]."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LLMResponseParseError(
            reason=f"{name}: must be list[str]",
            excerpt=raw[:_EXCERPT_LENGTH],
        )


def _parse_impact_report(raw: str) -> ImpactReport:
    """Defensively parse an LLM response into an ImpactReport.

    Prose and code fences are stripped (first-``{``-to-last-``}`` slice);
    JSONDecodeError is wrapped into LLMResponseParseError; the shape is
    validated as a dict with exactly the six contract keys and the documented
    value types. risk is coerced to upper and falls back to MEDIUM (with a
    WARNING) when outside {HIGH, MEDIUM, LOW}.

    Args:
        raw: raw model output, possibly wrapped in prose or code fences.

    Returns:
        The validated ImpactReport.

    Raises:
        LLMResponseParseError: on bad JSON, a non-dict, wrong keys, a wrong
            value type, or an empty payload.
    """
    stripped = _strip_prose_and_fences(raw)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMResponseParseError(
            reason=str(exc),
            excerpt=raw[:_EXCERPT_LENGTH],
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMResponseParseError(
            reason="not a dict",
            excerpt=raw[:_EXCERPT_LENGTH],
        )
    if set(parsed.keys()) != _REPORT_KEYS:
        raise LLMResponseParseError(
            reason="keys must be summary+risk+modified+affected+requirements+checklist",
            excerpt=raw[:_EXCERPT_LENGTH],
        )

    _require_str(parsed["summary"], "summary", raw)
    _require_str(parsed["risk"], "risk", raw)
    _require_str_list(parsed["modified"], "modified", raw)
    _require_str_list(parsed["affected"], "affected", raw)
    _require_str_list(parsed["requirements"], "requirements", raw)
    _require_str_list(parsed["checklist"], "checklist", raw)

    risk = parsed["risk"].upper()
    if risk not in _VALID_RISK:
        logger.warning(
            "invalid risk, falling back to MEDIUM",
            extra={"risk": parsed["risk"]},
        )
        risk = "MEDIUM"

    return ImpactReport(
        summary=parsed["summary"],
        risk=risk,
        modified=parsed["modified"],
        affected=parsed["affected"],
        requirements=parsed["requirements"],
        checklist=parsed["checklist"],
    )


def run_plan(project_root: pathlib.Path) -> str:
    """Analyze spec changes and return the Markdown Impact Report.

    Ten-step orchestrator: validate env, load config, load the traceability
    graph (raising if absent), parse baseline + fresh (cloned) specs and
    classify the endpoint diff, short-circuit on no changes, map changes onto
    the graph for affected endpoints, build the prompts, ask the LLM (single
    turn), and parse + render the report.

    Args:
        project_root: root of the Swax project. ``.swax/config.yml`` describes
            the local specs root and git coordinates; ``.swax/traceability.yml``
            holds the graph (produced by ``swax discover``).

    Returns:
        The Impact Report rendered as Markdown.

    Raises:
        MissingEnvironmentVariablesError: when an LLM credential is missing
            (propagated from require_vars).
        TraceabilityGraphMissingError: when ``.swax/traceability.yml`` is
            absent (raised by run_plan, not load_traceability).
        SpecParseError: when a discovered spec cannot be parsed (propagated).
        RepositoryCloneError: when cloning the specs repo fails (propagated).
        SpecsNotFoundError: when the specs subdir is absent in the clone
            (propagated).
        UnsupportedLLMProtocolError: on an unknown SWAX_LLM_PROTOCOL
            (propagated from build_llm_client).
        LLMCallError: on a generic LLM API failure (propagated).
        LLMRateLimitedError: on an LLM rate-limit failure (propagated).
        LLMResponseParseError: when the LLM response cannot be parsed into the
            ImpactReport contract (raised by run_plan).
    """
    require_vars()
    logger.info("plan started", extra={"project_root": str(project_root)})

    config: Config = load_config(project_root / ".swax" / "config.yml")

    traceability_path = project_root / ".swax" / "traceability.yml"
    if not traceability_path.exists():
        raise TraceabilityGraphMissingError(path=traceability_path)
    graph: TraceabilityGraph = load_traceability(traceability_path)

    baseline_root = project_root / config.specs.location
    baseline = _parse_spec_map(discover_specs(baseline_root), baseline_root)
    with clone_specs(config.git.url, config.git.location) as fresh_root:
        fresh = _parse_spec_map(discover_specs(fresh_root), fresh_root)
        merged = _diff_and_classify(baseline, fresh)

    if not merged.has_changes():
        report = ImpactReport(
            summary="No changes detected",
            risk="LOW",
            modified=[],
            affected=[],
            requirements=[],
            checklist=[],
        )
        logger.info("plan completed: no changes")
        return render_impact_report(report)

    changed = merged.changed_paths()
    affected = find_affected_endpoints(changed, graph)
    graph_context, trimmed_affected = _build_graph_context(affected, changed, graph)
    system = build_impact_report_system_prompt()
    user = build_impact_report_user_prompt(
        added=merged.added,
        removed=merged.removed,
        modified=merged.modified,
        affected=trimmed_affected,
        graph_context=graph_context,
    )

    client: LLMClient = build_llm_client()
    raw = client.ask(system=system, user=user)
    report = _parse_impact_report(raw)

    logger.info(
        "plan completed",
        extra={"changed": len(changed), "affected": len(affected)},
    )
    return render_impact_report(report)


__all__: list[str] = ["run_plan"]
