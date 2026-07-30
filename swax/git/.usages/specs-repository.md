# Specs repository — cloning to read specifications

## Domain

Access templates for a remote git repository with OpenAPI/Swagger specifications. Target audience: cell `applications/init/` (clones the repository in order to copy specifications into the local project path).

Swax treats the repository as read-only: it clones, reads, and removes the temporary clone. No commits, no pushes.

---

## Cloning as a context manager

`clone_specs` is a context manager: it yields the path to the specifications inside the temporary clone and automatically cleans up the temporary directory on exit (whether normal or via exception):

```python
from pathlib import Path

from swax.git import clone_specs


def install_specs(repo_url: str, specs_location: str) -> Path:
    with clone_specs(repo_url, specs_location) as specs_path:
        # specs_path is valid only inside the with — after exit the directory is removed
        # copy_specs(source=specs_path, destination=local_path) — delegated to the `fs/` cell
        return list(specs_path.rglob("*.yaml"))
```

Consumer conventions:
- `repo_url` — clone URL. For private repositories, rely on git credential helpers; do not embed tokens in the URL.
- `specs_location` — subdirectory in the repository where the specifications live (from `GitConfig.location`).
- Using `with` is mandatory — the path is invalid outside the block.

---

## Domain exception handling

`clone_specs` raises two domain exceptions. The consumer (the `init` command's CLI handler) maps them to `click.ClickException` for a uniform exit:

```python
from swax.git import clone_specs, RepositoryCloneError, SpecsNotFoundError


def safe_clone(repo_url: str, specs_location: str):
    try:
        with clone_specs(repo_url, specs_location) as specs_path:
            yield specs_path
    except RepositoryCloneError as exc:
        # click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")
        ...
    except SpecsNotFoundError as exc:
        # click.ClickException(f"Specs not found at {exc.path}")
        ...
```

`RepositoryCloneError` carries `url` and `reason` — for a clear message to the user.
`SpecsNotFoundError` carries `path` — indicating which subdirectory is missing in the repository.

---

## Testing

In tests, `mock.patch` the `Repo.clone_from` call at its import point (conventions — Mocks). Do not perform a real clone in tests.
