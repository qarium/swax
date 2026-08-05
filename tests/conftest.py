"""Shared pytest configuration for the swax test-suite."""

import sys

# Python 3.10 resolves ``unittest.mock`` dotted patch targets via ``_dot_lookup``,
# which walks the path with ``getattr(package, submodule)``. Several swax package
# facades re-export a symbol under the same name as its submodule -- e.g.
# ``swax/git/__init__.py`` does ``from .clone_specs import clone_specs`` -- so that
# ``getattr`` returns the function and a patch like
# ``mocker.patch("swax.git.clone_specs.Repo.clone_from")`` fails with
# "does not have the attribute". Python 3.11+ switched mock to
# ``pkgutil.resolve_name``, which resolves through the import system and is immune
# to that shadowing (bpo-45816). Backport the 3.11+ resolution onto 3.10 so the
# suite is green without altering any cell contract, production code, or test.
if sys.version_info < (3, 11):
    import functools
    import pkgutil
    import unittest.mock

    def _resolve_target(target: str) -> tuple:
        target, attribute = target.rsplit(".", 1)
        return functools.partial(pkgutil.resolve_name, target), attribute

    unittest.mock._get_target = _resolve_target  # type: ignore[attr-defined]
