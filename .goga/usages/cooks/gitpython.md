# GitPython — Repository Cloning

## Domain

Patterns for cloning remote git repositories into a temporary working directory. Used by the `init` command to fetch OpenAPI specs and by `discover`/`plan` to access current spec state. Target audience: the `git/` cell.

The project repository is read-only from Swax's perspective — Swax clones, reads, and discards. No commits, no pushes.

---

## Clone Into Temporary Directory

Use `tempfile.TemporaryDirectory` as a context manager so cleanup is automatic even on failure.

```python
import pathlib
import tempfile

from git import Repo


def clone_specs(repo_url: str, specs_location: str) -> tuple[pathlib.Path, callable[[], None]]:
    """Clone the repo into a temp dir; return (specs_path, cleanup)."""
    tmp = tempfile.TemporaryDirectory(prefix="swax-")
    try:
        repo = Repo.clone_from(repo_url, tmp.name, depth=1)
        specs_path = pathlib.Path(tmp.name) / specs_location
        if not specs_path.exists():
            raise SpecsNotFoundError(specs_path)
        return specs_path, tmp.cleanup
    except Exception:
        tmp.cleanup()
        raise
```

`depth=1` performs a shallow clone — sufficient for reading the latest specs and avoids fetching the full history.

---

## Cleanup Discipline

Always pair clone with cleanup. If you forget `tmp.cleanup()`, the OS temp directory accumulates stray directories.

```python
specs_path, cleanup = clone_specs(repo_url, location)
try:
    yield specs_path
finally:
    cleanup()
```

Wrap as a context manager when reuse is needed:

```python
@contextlib.contextmanager
def cloned_repo(repo_url: str, specs_location: str) -> typing.Iterator[pathlib.Path]:
    with tempfile.TemporaryDirectory(prefix="swax-") as tmp:
        Repo.clone_from(repo_url, tmp, depth=1)
        yield pathlib.Path(tmp) / specs_location
```

Prefer this form — `TemporaryDirectory` cleanup runs even on exception.

---

## Error Mapping

Catch GitCommandError and convert to a domain exception with the failing URL.

```python
from git.exc import GitCommandError

try:
    Repo.clone_from(repo_url, tmp, depth=1)
except GitCommandError as exc:
    raise RepositoryCloneError(url=repo_url, reason=str(exc)) from exc
```

---

## Authentication

For private repositories, rely on git's existing credential helpers — Swax does not manage credentials. Document this expectation; do not pass tokens via the URL.

```python
# Correct: git resolves credentials from the environment
Repo.clone_from(repo_url, tmp, depth=1)

# Forbidden: embedding tokens in URLs leaks them into logs
# Repo.clone_from(f"https://{token}@host/repo", ...)
```