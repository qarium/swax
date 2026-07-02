"""Storage routines: YAML (de)serialization of TraceabilityGraph.

load_traceability reads .swax/traceability.yml (UTF-8, safe loader) into a
TraceabilityGraph, normalizing each adjacency value to a list and treating an
empty or missing file as an empty graph. save_traceability dumps the graph to
deterministic YAML, sorting edges by key and each adjacency list by value
explicitly in Python and creating parent directories so the output reads
cleanly in diffs. Both operate on pathlib.Path values.
"""

import pathlib

import yaml

from .TraceabilityGraph import TraceabilityGraph


def load_traceability(path: pathlib.Path) -> TraceabilityGraph:
    """Read and normalize a traceability YAML file into a TraceabilityGraph.

    Args:
        path: location of the traceability file (e.g. .swax/traceability.yml).

    An empty or missing file yields an empty graph, not an error. Each
    adjacency value is normalized to a list: a list value is copied, any other
    (scalar) value is wrapped as a single-element list.
    """
    raw_text = path.read_text(encoding="utf-8") if path.exists() else ""
    data = yaml.safe_load(raw_text) or {}
    if not isinstance(data, dict):
        # A non-mapping payload (e.g. a bare scalar in a corrupt file) is treated
        # like an empty/missing file rather than crashing on .items() below.
        data = {}
    normalized: dict[str, list[str]] = {}
    for key, value in data.items():
        normalized[key] = list(value) if isinstance(value, list) else [value]
    return TraceabilityGraph(edges=normalized)


def save_traceability(graph: TraceabilityGraph, path: pathlib.Path) -> None:
    """Persist a TraceabilityGraph to a YAML file with deterministic formatting.

    Args:
        graph: the graph instance to serialize. The caller should invoke
            deduplicate first.
        path: destination file path; parent directories are created.

    The edges mapping is sorted by key and each adjacency list by value
    explicitly in Python, then dumped with sort_keys=False,
    allow_unicode=True, default_flow_style=False so repeated writes produce
    byte-identical files.
    """
    payload = graph.model_dump(mode="json")
    ordered = {key: sorted(value) for key, value in sorted(payload["edges"].items())}
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(
        ordered,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    path.write_text(yaml_text, encoding="utf-8")


__all__: list[str] = [
    "load_traceability",
    "save_traceability",
]
