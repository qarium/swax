"""Specs repository cloning as a context manager.

clone_specs shallow-clones the remote repository into a temporary directory
and yields the path to the specs subdirectory for the duration of the with
block. Cleanup of the temporary directory is guaranteed by
tempfile.TemporaryDirectory on every outcome — normal exit or exception.
"""

import contextlib
import pathlib
import tempfile
from collections.abc import Iterator

from git import Repo
from git.exc import GitCommandError

from .errors import RepositoryCloneError, SpecsNotFoundError


@contextlib.contextmanager
def clone_specs(repo_url: str, specs_location: str) -> Iterator[pathlib.Path]:
    """Clone the repository and yield the specs subdirectory path.

    Args:
        repo_url: clone URL of the repository holding API specifications.
        specs_location: subdirectory inside the repository where specs live.

    Yields:
        Path to the specs directory inside the clone, valid only within the
        context — the temporary directory is deleted on exit.

    Raises:
        RepositoryCloneError: if GitPython fails to clone the repository.
        SpecsNotFoundError: if the declared specs_location does not exist
            inside the clone.
    """
    with tempfile.TemporaryDirectory(prefix="swax-") as tmp:
        tmp_path = pathlib.Path(tmp)

        try:
            Repo.clone_from(repo_url, tmp_path, depth=1)
        except GitCommandError as exc:
            raise RepositoryCloneError(url=repo_url, reason=str(exc)) from exc

        specs_path = tmp_path / specs_location
        if not specs_path.exists():
            raise SpecsNotFoundError(path=specs_path)

        yield specs_path


__all__: list[str] = [
    "clone_specs",
]
