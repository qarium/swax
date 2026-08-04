"""Structural diff between two dereferenced specifications.

diff_specs computes a raw DeepDiff between a baseline spec and a current spec
(both fully dereferenced by parse_spec). It performs no classification — that
is classify_endpoint_changes' job. The DeepDiff kwargs are fixed per the
deepdiff usage: endpoint order is ignored, identical subtrees are skipped
early, and the production path never uses verbose_level=2.
"""

from deepdiff import DeepDiff


def diff_specs(base: dict, current: dict) -> DeepDiff:
    """Compute a structural diff between two dereferenced specs.

    Args:
        base: baseline (local) spec dict — output of parse_spec.
        current: fresh (cloned repo) spec dict — output of parse_spec.

    Returns:
        A DeepDiff result consumed by classify_endpoint_changes.
    """
    return DeepDiff(
        base,
        current,
        ignore_order=True,
        report_repetition=False,
        cutoff_intersection_for_pairs=1,
        verbose_level=1,
    )


__all__: list[str] = [
    "diff_specs",
]
