"""Domain error entities for the git cell.

Both errors are keyword-only Exception subclasses. They store their contract
fields as public attributes (exc.url, exc.reason, exc.path) and expose a
deterministic string form so the CLI handlers can surface them to users
without leaking anything sensitive (no credentials are ever carried — private
repositories rely on git credential helpers).
"""

import pathlib


class RepositoryCloneError(Exception):
    """Raised by clone_specs when cloning the repository fails.

    Args:
        url: clone URL that failed.
        reason: original error message from GitPython.
    """

    def __init__(self, *, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"url={url!r}, reason={reason!r}")


class SpecsNotFoundError(Exception):
    """Raised by clone_specs when the declared specs_location is absent.

    Args:
        path: expected path that was not found inside the clone.
    """

    def __init__(self, *, path: pathlib.Path) -> None:
        self.path = path
        super().__init__(f"path={path!r}")


__all__: list[str] = [
    "RepositoryCloneError",
    "SpecsNotFoundError",
]
