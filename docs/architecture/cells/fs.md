---
title: swax/fs
description: Filesystem layout of a Swax project — .swax/ directory, spec copying, and transactional spec mirroring.
---

# `swax/fs`

Filesystem layout of a Swax project: the `.swax/` directory, spec copying, and
transactional spec mirroring.

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

## Spec mirroring

Mirroring a remote specs state onto the local specs directory — the
foundation of `swax update`. The remote clone is the source of truth:
mirroring overwrites local edits silently.

### `compare_specs(local_root: pathlib.Path, remote_root: pathlib.Path) -> changes: SpecsChanges`

Read-only, byte-level classification of two directory trees.

- `local_root`: the live local specs directory (may be absent — every remote
  file is then classified as added).
- `remote_root`: the specs directory inside the fresh clone.
- `changes`: the `SpecsChanges` classification driving every downstream
  branch of `run_update`.

Algorithm:

1. Index both trees by POSIX-relative path (files only).
2. `added` = remote-only, `removed` = local-only, both sorted.
3. `updated` = files present on both sides whose bytes differ
   (`filecmp.cmp(..., shallow=False)` — mtime/permissions differences are
   not reported).

Requirements:

- Deterministic sorted output; read-only — neither tree is mutated.
- A missing `local_root` or an empty `remote_root` are defined cases, not
  errors.

### `SpecsChanges(added, updated, removed)`

Pydantic value object (`kw_only=True`, list fields with `default_factory=list`).

- `has_changes()` — any of the three lists non-empty.
- `has_additions()` — `added` or `updated` non-empty; **drives the
  LLM-requiring branch** (`False` for a removals-only diff).
- Default-constructed instance reports no changes.

### `validate_specs_location(project_root: pathlib.Path, specs_location: pathlib.Path)`

Path guard for the mirroring target. Runs before any mutation.

- Accepts only locations **strictly inside the project** that do not cover
  `.swax/` — the swap replaces the whole directory, so swax must not delete
  a directory it does not own.
- Refuses targets outside the project, the project root itself, its
  ancestors, and anything covering the `.swax/` directory — mirroring would
  destroy a directory swax does not own, the project, or its saved state.
- Raises `UnsafeSpecsLocationError` carrying the refused location.

### `UnsafeSpecsLocationError(*, path: pathlib.Path)`

Domain error raised by `validate_specs_location`; keyword-only constructor
storing `self.path`.

### `staged_specs_swap(target: pathlib.Path, staging: pathlib.Path) -> Iterator[live_root: pathlib.Path]`

`@contextlib.contextmanager` — transactional replacement of the live specs
directory; the single rollback point of the update transaction.

- Enter: remove a stale leftover backup, rename `target` to
  `.{target.name}.backup`, rename `staging` into place, yield the live root.
  A missing `target` is a defined case — nothing is backed up.
- Normal exit: remove the backup (best effort — a stale leftover is removed
  on the next swap).
- Exception: remove the swapped-in directory, restore the backup (nothing to
  restore when `target` was missing), re-raise.

Constraints:

- Renames stay inside `target.parent` (same filesystem, atomic).
- Does not build `staging`; never touches anything outside `target.parent`.

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
- [Architecture / applications/update cell](applications.md#swaxapplicationsupdate) —
  the mirroring consumer.
