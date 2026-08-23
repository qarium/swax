"""Application use-case: update local specs to the remote state (transactional).

run_update mirrors the local specs directory to the remote state described by
the saved configuration and rebuilds the traceability graph conditionally, as
one transaction. The remote clone is the source of truth — local spec edits
are overwritten silently. Branch priority, checked top to bottom:

- empty file diff — nothing is touched, no LLM, the graph stays as is (or
  stays missing): "Specs are up to date."
- removals-only diff — the graph is pruned deterministically when a graph
  file exists (no LLM); when it does not, the specs are applied and the graph
  stays missing, still without an LLM call;
- added/updated files — LLM credentials are validated BEFORE any mutation;
  the graph is revised incrementally when it exists, or built from scratch
  via the sibling run_discover when it does not.

staged_specs_swap is the single rollback point: a failure of the rebuild
block removes the swapped-in specs, restores the backup, and is then wrapped
into GraphRebuildFailedError. Failures before the swap propagate raw. The
LLM response is parsed defensively (fence stripping, JSONDecodeError wrapped
into LLMResponseParseError, dict[str, list[str]] shape validation) and
filtered to the endpoint universe. SWAX_LLM_TOKEN never appears in logs or in
the returned output.
"""

import json
import logging
import pathlib
import shutil

import yaml

from ...config import load_config, require_vars
from ...fs import SpecsChanges, compare_specs, copy_specs, staged_specs_swap, validate_specs_location
from ...git import clone_specs
from ...llm import (
    LLMCallError,
    LLMClient,
    LLMRateLimitedError,
    LLMResponseParseError,
    UnsupportedLLMProtocolError,
    build_llm_client,
)
from ...openapi import (
    EndpointDiff,
    SpecParseError,
    classify_endpoint_changes,
    diff_specs,
    discover_specs,
    extract_paths,
    extract_schemas,
    parse_spec,
)
from ...prompts import (
    build_incremental_graph_system_prompt,
    build_incremental_graph_user_prompt,
)
from ...traceability import TraceabilityGraph, load_traceability
from ..discover import run_discover
from .errors import GraphRebuildFailedError
from .render_update_summary import render_update_summary
from .save_traceability_atomically import save_traceability_atomically

logger = logging.getLogger(__name__)

_EXCERPT_LENGTH = 200


def _strip_prose_and_fences(raw: str) -> str:
    """Return the substring spanning the first ``{`` to the last ``}``.

    If the payload contains no balanced braces, it is returned unchanged so
    ``json.loads`` raises an informative error. Mirrors the defensive parser
    convention of run_discover and run_plan.
    """
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace > last_brace:
        return raw

    return raw[first_brace : last_brace + 1]


def _parse_incremental_response(raw: str) -> dict[str, list[str]]:
    """Defensively parse the LLM response into a dependency mapping.

    Prose and code fences are stripped (first-``{``-to-last-``}`` slice);
    json.JSONDecodeError is wrapped into LLMResponseParseError with a raw
    excerpt; the shape must be dict[str, list[str]].

    Args:
        raw: raw model output, possibly wrapped in prose or code fences.

    Returns:
        The validated source-path -> dependent-paths mapping.

    Raises:
        LLMResponseParseError: on bad JSON, a non-dict payload, or a value
            that is not a list of strings.
    """
    stripped = _strip_prose_and_fences(raw)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMResponseParseError(reason=str(exc), excerpt=raw[:_EXCERPT_LENGTH]) from exc

    shape_matches = isinstance(parsed, dict) and all(
        isinstance(value, list) and all(isinstance(item, str) for item in value) for value in parsed.values()
    )
    if not shape_matches:
        raise LLMResponseParseError(
            reason="shape mismatch: expected dict[str, list[str]]",
            excerpt=raw[:_EXCERPT_LENGTH],
        )

    return parsed


def _filter_to_universe(deps: dict[str, list[str]], universe: set[str]) -> dict[str, list[str]]:
    """Restrict a dependency mapping to the endpoint universe.

    Sources outside the universe are dropped and targets outside it are
    removed from the surviving lists; every universe endpoint is then
    guaranteed a node (empty adjacency list) via setdefault — the full-graph
    node coverage the incremental prompt asks for.

    Args:
        deps: parsed LLM dependency mapping.
        universe: the complete endpoint universe after the update.

    Returns:
        The filtered mapping covering exactly the universe endpoints.
    """
    filtered = {
        source: [target for target in targets if target in universe]
        for source, targets in deps.items()
        if source in universe
    }

    for endpoint in universe:
        filtered.setdefault(endpoint, [])

    return filtered


def _relative_spec_files(root: pathlib.Path) -> set[str]:
    """Return the POSIX relative paths of the spec files under root.

    Args:
        root: specs directory (the local live directory or the remote clone).

    Returns:
        Set of relative paths of the files passing the spec membership
        filter; a missing root yields an empty set.
    """
    return {path.relative_to(root).as_posix() for path in discover_specs(root)}


def _classify_spec_changes(
    local_root: pathlib.Path,
    remote_root: pathlib.Path,
    changes: SpecsChanges,
) -> tuple[set[str], set[str], list[str], set[str]]:
    """Filter the file classification to spec files and collect prune endpoints.

    Spec files are filtered by membership in discover_specs over both roots;
    non-spec files are mirrored silently but never parsed. The endpoints of
    the removed spec files are read from their last local content and
    reconciled against the untouched surviving (remote) specs: an endpoint
    dropped with one file but still declared by any surviving spec stays
    live — the prune list shared by both branches covers only endpoints
    absent from the whole post-update tree. Surviving endpoints are read
    only when something can be dropped (removed spec files or modified
    pairs); an untouched survivor that fails to parse is skipped with a
    warning instead of failing the run — untouched files are outside the
    parse scope the contract pins (removed, modified, and added files only),
    so a broken untouched spec must not block the mirroring.

    Args:
        local_root: local specs directory (still the pre-swap content).
        remote_root: specs directory inside the fresh clone.
        changes: file-level classification from compare_specs.

    Returns:
        A ``(modified_spec_rels, added_spec_rels, removed_endpoints,
        surviving_endpoints)`` tuple — surviving_endpoints is the endpoint
        set of the untouched remote specs (empty when nothing can be
        dropped), reused to reconcile the per-pair removals of the
        incremental branch the same way.

    Raises:
        SpecParseError: when a removed spec fails to parse (propagated).
    """
    local_spec_rels = _relative_spec_files(local_root)
    remote_spec_rels = _relative_spec_files(remote_root)
    removed_spec_rels = set(changes.removed) & local_spec_rels
    modified_spec_rels = set(changes.updated) & local_spec_rels & remote_spec_rels
    added_spec_rels = set(changes.added) & remote_spec_rels

    dropped_endpoints = {
        endpoint for rel in removed_spec_rels for endpoint in extract_paths(parse_spec(local_root / rel))
    }

    if not dropped_endpoints and not modified_spec_rels:
        return modified_spec_rels, added_spec_rels, [], set()

    untouched_rels = remote_spec_rels - modified_spec_rels - added_spec_rels
    surviving_endpoints = _untouched_surviving_endpoints(remote_root, untouched_rels)
    removed_endpoints = sorted(dropped_endpoints - surviving_endpoints)

    return modified_spec_rels, added_spec_rels, removed_endpoints, surviving_endpoints


def _untouched_surviving_endpoints(remote_root: pathlib.Path, untouched_rels: set[str]) -> set[str]:
    """Collect the endpoints of the untouched remote specs, best effort.

    Args:
        remote_root: specs directory inside the fresh clone.
        untouched_rels: relative spec paths neither removed nor modified
            nor added — byte-identical in both trees.

    Returns:
        The union of the specs' endpoint sets. An untouched spec that fails
        to parse contributes nothing and is skipped with a warning: the run
        must not abort on files the mirroring itself never parses.
    """
    surviving: set[str] = set()

    for rel in sorted(untouched_rels):
        try:
            surviving.update(extract_paths(parse_spec(remote_root / rel)))
        except SpecParseError:
            logger.warning(
                "surviving spec not parseable; skipped by endpoint reconciliation",
                extra={"spec": rel},
            )

    return surviving


def _merged_endpoint_diff(  # noqa: PLR0913, PLR0917 — the reconciliation set needs the added endpoints
    local_root: pathlib.Path,
    remote_root: pathlib.Path,
    modified_spec_rels: set[str],
    removed_endpoints: list[str],
    surviving_endpoints: set[str],
    added_endpoints: list[str],
) -> EndpointDiff:
    """Classify and merge the endpoint diff of every modified spec-file pair.

    Each modified spec file is parsed on both sides and diffed; the per-pair
    buckets are unioned as sets and sorted once at the end for determinism.
    The endpoints of the whole-file removals are folded into the merged
    removed list — removed spec files are pruned in the same revision. All
    removals are reconciled against the endpoints still declared by the
    post-update tree — the untouched survivors, the modified pairs' remote
    sides, and the added specs: an endpoint dropped by one file but still
    declared anywhere stays live, exactly like a whole-file removal.

    Args:
        local_root: local specs directory (still the pre-swap content).
        remote_root: specs directory inside the fresh clone.
        modified_spec_rels: relative paths changed and present on both sides.
        removed_endpoints: endpoints of the locally removed spec files.
        surviving_endpoints: endpoints of the untouched remote specs (from
            _classify_spec_changes).
        added_endpoints: endpoints of the newly added spec files (from
            _added_spec_context) — the last member of the reconciliation set.

    Returns:
        A single EndpointDiff with deterministic, sorted buckets.

    Raises:
        SpecParseError: when either side of a pair fails to parse (propagated).
    """
    added: set[str] = set()
    removed: set[str] = set(removed_endpoints)
    modified: dict[str, set[str]] = {}
    still_declared: set[str] = set(surviving_endpoints) | set(added_endpoints)

    for rel in sorted(modified_spec_rels):
        local_spec = parse_spec(local_root / rel)
        remote_spec = parse_spec(remote_root / rel)
        still_declared.update(extract_paths(remote_spec))
        pair = classify_endpoint_changes(diff_specs(local_spec, remote_spec))
        added.update(pair.added)
        removed.update(pair.removed)
        for endpoint, descriptions in pair.modified.items():
            modified.setdefault(endpoint, set()).update(descriptions)

    removed -= still_declared

    return EndpointDiff(
        added=sorted(added),
        removed=sorted(removed),
        modified={endpoint: sorted(descriptions) for endpoint, descriptions in sorted(modified.items())},
    )


def _added_spec_context(remote_root: pathlib.Path, added_spec_rels: set[str]) -> tuple[list[str], dict]:
    """Collect the endpoints and schemas of the newly added spec files.

    Args:
        remote_root: specs directory inside the fresh clone.
        added_spec_rels: relative paths present only in the remote state.

    Returns:
        A ``(endpoints, schemas)`` tuple — the LLM context of the added specs.
        The endpoints are unioned across the added files (an endpoint declared
        by several of them appears once); the schemas are attached to the
        prompt only, never persisted.

    Raises:
        SpecParseError: when an added spec fails to parse (propagated).
    """
    endpoints: set[str] = set()
    schemas: dict = {}

    for rel in sorted(added_spec_rels):
        spec = parse_spec(remote_root / rel)
        endpoints.update(extract_paths(spec))
        schemas.update(extract_schemas(spec))

    return sorted(endpoints), schemas


def _assemble_staging(remote_root: pathlib.Path, local_root: pathlib.Path) -> pathlib.Path:
    """Assemble the staging directory next to the live specs directory.

    A stale staging leftover from a crashed run is removed first — copy_specs
    merges, so without the guard a stale file would leak into the mirror.

    Args:
        remote_root: specs directory inside the fresh clone.
        local_root: local live specs directory; the staging sibling is built
            in its parent.

    Returns:
        The assembled staging directory, ready for staged_specs_swap.
    """
    staging = local_root.parent / ".specs-staging"
    shutil.rmtree(staging, ignore_errors=True)
    copy_specs(remote_root, staging)
    logger.debug("staging assembled", extra={"staging": staging.name})

    return staging


def _prune_graph(graph_path: pathlib.Path, removed_endpoints: list[str]) -> None:
    """Prune the removed endpoints from the existing graph and persist it.

    Graph-lifecycle sequencing: load, remove_paths, deduplicate, atomic save.

    Args:
        graph_path: location of the traceability file (.swax/traceability.yml).
        removed_endpoints: endpoints of the removed spec files.
    """
    graph = load_traceability(graph_path)
    graph.remove_paths(removed_endpoints)
    graph.deduplicate()
    save_traceability_atomically(graph, graph_path)


def _revise_graph_incrementally(
    graph_path: pathlib.Path,
    existing: TraceabilityGraph,
    merged: EndpointDiff,
    added_endpoints: list[str],
    added_schemas: dict,
) -> None:
    """Revise the existing graph from a single-turn LLM call and persist it.

    Builds the incremental prompt pair from the existing graph and the
    prepared change context, asks the LLM once, parses the response
    defensively, filters it to the endpoint universe, and persists the
    deduplicated graph atomically.

    Args:
        graph_path: location of the traceability file (.swax/traceability.yml).
        existing: the graph as it was before the update.
        merged: merged endpoint diff of the modified spec-file pairs, with
            the removed-file endpoints folded into its removed list.
        added_endpoints: endpoints of the newly added spec files.
        added_schemas: schemas of the newly added spec files (prompt context).

    Raises:
        LLMResponseParseError: when the LLM response cannot be parsed into
            dict[str, list[str]] (raised by the defensive parser).
    """
    system = build_incremental_graph_system_prompt()
    user = build_incremental_graph_user_prompt(
        existing.edges,
        merged.added,
        merged.removed,
        merged.modified,
        added_endpoints,
        added_schemas,
    )

    client: LLMClient = build_llm_client()
    raw = client.ask(system=system, user=user)

    deps = _parse_incremental_response(raw)
    universe = (set(existing.edges) - set(merged.removed)) | set(merged.added) | set(added_endpoints)
    edges = _filter_to_universe(deps, universe)

    graph = TraceabilityGraph(edges=edges)
    graph.deduplicate()
    save_traceability_atomically(graph, graph_path)


def run_update(project_root: pathlib.Path) -> str:
    """Mirror local specs to the remote state and rebuild the graph as one transaction.

    Algorithm: load config, guard the mirroring target, clone the remote
    state, classify the file diff; an empty diff returns the up-to-date
    message untouched. Otherwise classify the spec-file changes, validate LLM
    credentials when the diff has additions (before any mutation), prepare
    the incremental input when a graph file exists, assemble the staging
    directory, and swap it in — the rebuild inside the swap (deterministic
    prune, incremental LLM revision, or delegated run_discover; the existing
    graph is loaded inside it too, so a corrupt graph rolls back like any
    rebuild failure) is the single rollback point whose failures are wrapped
    into GraphRebuildFailedError after the specs have been restored.

    Args:
        project_root: root of the Swax project. ``.swax/config.yml`` describes
            the remote source and the local specs layout;
            ``.swax/traceability.yml`` is updated according to the diff.

    Returns:
        The terminal summary text (change groups plus the graph status line).

    Raises:
        UnsafeSpecsLocationError: when the configured specs location covers
            the project itself (propagated before any mutation).
        RepositoryCloneError: when cloning the specs repo fails (propagated).
        SpecsNotFoundError: when the specs subdir is absent in the clone
            (propagated).
        MissingEnvironmentVariablesError: when an LLM credential is missing
            and the diff has additions — raised before any mutation.
        SpecParseError: when a spec needed for classification fails to parse
            (propagated unwrapped outside the rebuild block).
        GraphRebuildFailedError: when the graph rebuild after applying the
            specs fails — the specs have been restored from the backup at
            that point; a failed first build leaves no graph file behind.
    """
    logger.info("update started", extra={"project_root": str(project_root)})

    config = load_config(project_root / ".swax" / "config.yml")

    local_root = project_root / pathlib.Path(config.specs.location)
    graph_path = project_root / ".swax" / "traceability.yml"

    validate_specs_location(project_root=project_root, specs_location=local_root)

    with clone_specs(config.git.url, config.git.location) as remote_root:
        changes = compare_specs(local_root=local_root, remote_root=remote_root)

        if not changes.has_changes():
            logger.info("update completed: no changes", extra={"project_root": str(project_root)})
            return "Specs are up to date."

        logger.debug(
            "classified changes",
            extra={
                "added": len(changes.added),
                "updated": len(changes.updated),
                "removed": len(changes.removed),
            },
        )

        modified_spec_rels, added_spec_rels, removed_endpoints, surviving_endpoints = _classify_spec_changes(
            local_root=local_root,
            remote_root=remote_root,
            changes=changes,
        )
        graph_existed = graph_path.exists()

        if changes.has_additions():
            require_vars()

            if graph_existed:
                added_endpoints, added_schemas = _added_spec_context(
                    remote_root=remote_root,
                    added_spec_rels=added_spec_rels,
                )
                merged = _merged_endpoint_diff(
                    local_root=local_root,
                    remote_root=remote_root,
                    modified_spec_rels=modified_spec_rels,
                    removed_endpoints=removed_endpoints,
                    surviving_endpoints=surviving_endpoints,
                    added_endpoints=added_endpoints,
                )

        staging = _assemble_staging(remote_root=remote_root, local_root=local_root)

        graph_status: str | None = None

        try:
            with staged_specs_swap(target=local_root, staging=staging):
                if not changes.has_additions():
                    if graph_path.exists():
                        logger.debug(
                            "rebuild branch: prune",
                            extra={"removed_endpoints": len(removed_endpoints)},
                        )
                        _prune_graph(graph_path, removed_endpoints)
                        graph_status = "rebuilt"
                elif graph_existed:
                    existing = load_traceability(graph_path)
                    logger.debug(
                        "rebuild branch: incremental",
                        extra={"existing_endpoints": len(existing.edges)},
                    )
                    _revise_graph_incrementally(
                        graph_path=graph_path,
                        existing=existing,
                        merged=merged,
                        added_endpoints=added_endpoints,
                        added_schemas=added_schemas,
                    )
                    graph_status = "rebuilt"
                else:
                    logger.debug("rebuild branch: full", extra={"project_root": str(project_root)})
                    run_discover(project_root)
                    graph_status = "built"

                if graph_status is not None:
                    logger.debug("graph persisted", extra={"graph_status": graph_status})
        # ValueError/TypeError cover corrupt-input failures that are not
        # OSError or yaml.YAMLError: a binary graph file (UnicodeDecodeError),
        # a non-string adjacency (pydantic ValidationError), or an
        # unserializable payload scalar — all rebuild-block failures, so all
        # wrapped per the contract.
        except (
            SpecParseError,
            LLMCallError,
            LLMRateLimitedError,
            UnsupportedLLMProtocolError,
            LLMResponseParseError,
            OSError,
            yaml.YAMLError,
            ValueError,
            TypeError,
        ) as exc:
            if not graph_existed and graph_path.exists():
                graph_path.unlink()

            raise GraphRebuildFailedError(reason=str(exc)) from exc

    output = render_update_summary(changes, graph_status)
    logger.info(
        "update completed",
        extra={
            "project_root": str(project_root),
            "added": len(changes.added),
            "updated": len(changes.updated),
            "removed": len(changes.removed),
            "graph_status": graph_status,
        },
    )
    return output


__all__: list[str] = ["run_update"]
