---
title: swax/git
description: Read-only access to the git repository holding specifications via GitPython.
---

# `swax/git`

Read-only access to the git repository holding specifications. Swax never
commits or pushes — clone, read, discard the clone.

## Routines

### `clone_specs(repo_url, specs_location) -> Iterator[specs_path: pathlib.Path]`

Context manager: clones the repository into a temporary directory and yields
the path to the specs subdirectory for the duration of the `with` block.
Cleanup is guaranteed even on exception.

- `repo_url`: clone URL of the repository holding API specifications.
- `specs_location`: subdirectory inside the repository where specs live.
- `specs_path`: path to the specs directory inside the clone, valid **only**
  within the context.

Algorithm:

1. Create a temporary directory and **shallow-clone** the repository into it.
2. Locate the specs subdirectory inside the clone.
3. Yield the resolved path.
4. On exit (normal or exception) remove the temporary directory.

Requirements:

- **Shallow clone** — only the latest commit is needed.
- The temporary directory is cleaned up on **every** outcome.
- GitPython errors are wrapped into `RepositoryCloneError` with the URL and
  reason.

Constraints:

- Credentials are **not** embedded in the URL — private repositories rely on
  git credential helpers.
- The yielded path does **not** outlive the context — the temporary directory
  is deleted on exit.

## Usage

```python
from swax.git import clone_specs

with clone_specs(repo_url, specs_location) as specs_path:
    # specs_path is valid only inside the with — after exit the directory is removed
    for f in specs_path.rglob("*.yaml"):
        ...
```

`with` is **mandatory** — the path is invalid outside the block.

## Errors

| Exception | Cause |
| --- | --- |
| `RepositoryCloneError(url: str, reason: str)` | Raised by `clone_specs` when cloning the repository fails. Carries the clone URL and original GitPython error message. |
| `SpecsNotFoundError(path: pathlib.Path)` | Raised by `clone_specs` when the declared `specs_location` does not exist inside the clone. Carries the expected path. |

Both exceptions propagate through the application layer; the CLI handler in
`commands/init` and `commands/plan` maps them to `click.ClickException`:

- `RepositoryCloneError` → `Failed to clone <url>: <reason>`
- `SpecsNotFoundError` → `Specs not found at <path>`

## See also

- [Architecture / fs cell](fs.md) — `copy_specs` consumes the yielded path.
- [Architecture / applications/init cell](applications.md#swaxapplicationsinit) —
  orchestrates clone → copy.
