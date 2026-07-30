# Initialize project — Swax initialization use case

## Domain

Invocation template for the Swax project initialization use case. Target audience: cell `commands/init/` (the CLI handler collects inputs from interactive prompts and delegates to `run_init`).

The use case orchestrates three domain cells: `config/` (write configuration), `git/` (clone the repository), `fs/` (create `.swax/` and copy specifications). This is a hexagonal application layer — no business logic, only a sequence of calls.

---

## Running the use case

`run_init` accepts all inputs explicitly — for testability and independence from the CLI:

```python
from pathlib import Path

from swax.applications.init import run_init


def initialize(repo_url: str, specs_location: str, download_path: Path, project_root: Path) -> None:
    run_init(
        repo_url=repo_url,
        specs_location=specs_location,
        download_path=download_path,
        project_root=project_root,
    )
```

Consumer conventions:
- `repo_url` — clone URL of the repository (from an interactive prompt).
- `specs_location` — subdirectory in the repository containing the specifications.
- `download_path` — local path where specifications are saved.
- `project_root` — project root (typically `pathlib.Path.cwd()`).

---

## What runs inside

The use case performs the steps in a strictly defined order:

1. Build a `Config` with `GitConfig` and `SpecsConfig` from the inputs.
2. Create `.swax/` via `ensure_swax_dir`.
3. Save `.swax/config.yml` via `save_config` — configuration is written BEFORE cloning, so the user can inspect it even if cloning fails.
4. Clone the repository via `clone_specs` (context manager — cleanup is guaranteed).
5. Copy specifications from the temporary clone to `download_path` via `copy_specs`.

---

## Domain exception handling

`run_init` does NOT catch exceptions from `git/` (`RepositoryCloneError`, `SpecsNotFoundError`) — they propagate upward. The CLI handler in `commands/init/` maps them to `click.ClickException`:

```python
from swax.applications.init import run_init
from swax.git import RepositoryCloneError, SpecsNotFoundError


def safe_initialize(repo_url, specs_location, download_path, project_root):
    try:
        run_init(repo_url, specs_location, download_path, project_root)
    except RepositoryCloneError as exc:
        # click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")
        ...
    except SpecsNotFoundError as exc:
        # click.ClickException(f"Specs not found at {exc.path}")
        ...
```

This is the separation of concerns: the application layer knows nothing about the CLI/Click — it only orchestrates the domain cells.

---

## Testing

`run_init` accepts all inputs explicitly — it is tested without mocking the CLI. Use `tmp_path` for `project_root` and `download_path`:

```python
def test_run_init_persists_config(tmp_path):
    project_root = tmp_path
    download_path = tmp_path / "specs"
    # mock clone_specs and copy_specs at their import point for a unit test
    # or run an integration test with a real local git repository in tmp_path
    run_init("https://example.com/repo.git", "specs/", download_path, project_root)
    assert (project_root / ".swax" / "config.yml").exists()
```
