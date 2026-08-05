"""Classification of a raw structural diff into endpoint-level changes.

classify_endpoint_changes walks a DeepDiff's change sets by path string and
produces an EndpointDiff: endpoints added / removed under ``paths``, and
endpoints modified (each with a list of human-readable change descriptions).
Paths under ``components`` / ``definitions`` are skipped — because ``$ref`` is
already dereferenced by parse_spec, every consuming endpoint surfaces the
change under its own ``paths[...]`` entry, so the schema-level change is
redundant and must not leak as a report path.
"""

import re

from deepdiff import DeepDiff

from .endpoint_diff import EndpointDiff

# DeepDiff path keys look like ``root['paths']['/users']['get']...``. A key that
# contains the active quote char is escaped by switching the delimiter (e.g.
# ``["/x'y"]``), so segments are matched per-quoted-key rather than naively
# split on a single character.
_SEGMENT_RE = re.compile(r"""\['([^']*)'\]|\["([^"]*)"\]""")

# A DeepDiff path of exactly ``root['paths']['<endpoint>']`` has two segments
# (``paths`` and the endpoint key) and is the only shape that represents a
# genuine endpoint add/remove. Anything deeper under ``paths`` (a new method,
# response code, or parameter block) is a sub-field change on an endpoint that
# already exists and is therefore a modification, not a new/removed endpoint.
_ENDPOINT_SEGMENT_COUNT = 2


def _path_segments(path_str: str) -> list[str]:
    """Return the bracketed key segments of a DeepDiff path string.

    The leading ``root`` token carries no segment; every ``['k']`` / ``["k"]``
    bracket yields one key. Both quote styles are handled so escaped keys are
    parsed intact.

    Args:
        path_str: a DeepDiff path such as ``root['paths']['/users']['get']``.

    Returns:
        The ordered key segments (e.g. ``['paths', '/users', 'get']``).
    """
    return [single or double for single, double in _SEGMENT_RE.findall(path_str)]


def _extract_endpoint(path_str: str) -> str | None:
    """Return the endpoint captured by the ``root['paths']['<endpoint>']`` prefix.

    Args:
        path_str: a DeepDiff path string.

    Returns:
        The endpoint path when the path is under ``paths``, otherwise ``None``
        (for ``components``, ``definitions``, ``info``, ``servers``, ...).
    """
    segments = _path_segments(path_str)
    if len(segments) > 1 and segments[0] == "paths":
        return segments[1]
    return None


def _describe_change(path_str: str) -> str:
    """Return a short, human-readable description of the change after the endpoint.

    The tail segments (method / responses / parameters / schema fields ...) are
    lowercased and space-joined; the raw dict repr is never leaked.

    Args:
        path_str: a DeepDiff path string under ``paths``.

    Returns:
        A description such as ``"get responses 200 schema type changed"``.
    """
    tail = _path_segments(path_str)[2:]
    if not tail:
        return "changed"
    return f"{' '.join(tail).lower()} changed"


def classify_endpoint_changes(diff: DeepDiff) -> EndpointDiff:
    """Classify a raw structural diff into endpoint-level changes.

    Walks the real deepdiff categories — ``dictionary_item_added`` /
    ``dictionary_item_removed`` (ordered sets of path strings) and
    ``values_changed`` / ``type_changes`` / ``iterable_item_added`` /
    ``iterable_item_removed`` (dicts keyed by path string). The iterable
    categories are what deepdiff emits when an item is added to or removed from
    a JSON array under an endpoint (a ``parameters``, ``tags``, ``enum``, or
    ``required`` list); treating them as modifications is what surfaces a newly
    added query parameter or enum value. Paths not under ``paths`` (e.g.
    ``components`` / ``definitions``) are skipped. The result is sorted for
    determinism, since deepdiff category iteration order is not stable across
    processes.

    Args:
        diff: DeepDiff result from diff_specs.

    Returns:
        An EndpointDiff aggregating added, removed, and modified endpoints.
    """
    added: list[str] = []
    removed: list[str] = []
    modified: dict[str, list[str]] = {}

    for category, bucket in (
        ("dictionary_item_added", added),
        ("dictionary_item_removed", removed),
    ):
        for path_str in diff.get(category, []) or []:
            segments = _path_segments(path_str)
            if len(segments) < _ENDPOINT_SEGMENT_COUNT or segments[0] != "paths":
                continue
            endpoint = segments[1]
            if len(segments) == _ENDPOINT_SEGMENT_COUNT:
                if endpoint not in bucket:
                    bucket.append(endpoint)
            else:
                # A deeper key (a new method, response code, or parameter block)
                # is a sub-field change on an endpoint that already exists — a
                # modification, not a new/removed endpoint.
                modified.setdefault(endpoint, []).append(_describe_change(path_str))

    changed_value_paths = {
        **(diff.get("values_changed", {}) or {}),
        **(diff.get("type_changes", {}) or {}),
        **(diff.get("iterable_item_added", {}) or {}),
        **(diff.get("iterable_item_removed", {}) or {}),
    }
    for path_str in changed_value_paths:
        endpoint = _extract_endpoint(path_str)
        if endpoint is None:
            continue
        modified.setdefault(endpoint, []).append(_describe_change(path_str))

    return EndpointDiff(
        added=sorted(added),
        removed=sorted(removed),
        modified={key: sorted(values) for key, values in sorted(modified.items())},
    )


__all__: list[str] = [
    "classify_endpoint_changes",
]
