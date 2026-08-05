---
title: swax/fs
description: Filesystem layout of a Swax project — .swax/ directory and spec copying.
---

# `swax/fs`

Filesystem layout of a Swax project: the `.swax/` directory and spec copying.

All paths are `pathlib.Path`. Relative imports inside the cell. Tests exercise
filesystem operations only through `tmp_path`.

## Routines

### `ensure_swax_dir(project_root: pathlib.Path) -> swax_dir: pathlib.Path`

Guarantees the `.swax/` directory exists under the project root and returns its
path.

- `project_root`: root of the Swax project (where `.swax/` lives).
- `swax_dir`: the `.swax/` directory, ready for `config.yml` and
  `traceability.yml` writes.

Algorithm:

1. Resolve `.swax/` under `project_root`.
2. Create the directory (with `parents`, tolerating prior existence).
3. Return the resolved path.

Requirements:

- **Idempotent** — safe to call before every write.

### `copy_specs(source: pathlib.Path, destination: pathlib.Path)`

Copies downloaded specifications from the temporary clone into the local
project path.

- `source`: directory of specs inside the clone (output of `clone_specs`).
- `destination`: local path declared in `SpecsConfig.location`.

Algorithm:

1. Ensure parent directories of `destination` exist.
2. Recursively merge `source` into `destination`, overwriting existing files.

Requirements:

- Parent directories of the destination are created as needed.
- Existing files are **overwritten** on re-runs (spec updates).
- Directory structure of the source is preserved.

Constraints:

- **Symlinks** in the clone are **not** dereferenced — copied as regular files.

## Project layout

The Swax project on the filesystem:

```
<project_root>/
├── .swax/
│   ├── config.yml          # created via save_config
│   └── traceability.yml    # created later via save_traceability
└── <specs.location>/       # specifications land here via copy_specs
    └── *.yaml | *.json
```

`ensure_swax_dir` creates `.swax/` with `parents=True, exist_ok=True` — safe
to call repeatedly.

## See also

- [Project layout](../../guide/project-layout.md) — end-user guide.
- [Architecture / git cell](git.md) — `clone_specs` produces the source.
