---
title: Project layout
description: Filesystem layout of a Swax project — the .swax/ directory and the downloaded specs.
---

# Project layout

A Swax project has this shape on disk:

```
<project_root>/
├── .swax/
│   ├── config.yml          # written by `swax init`
│   └── traceability.yml    # written by `swax discover`
└── <specs.location>/       # specifications land here via copy_specs
    └── *.yaml | *.json
```

## `.swax/`

The internal state directory. Created on demand by `ensure_swax_dir`
(`parents=True, exist_ok=True`) — safe to call before every write.

- `config.yml` — project coordinates. See [Configuration](../getting-started/configuration.md#swaxconfigyml).
- `traceability.yml` — the API dependency graph. See
  [Traceability graph](traceability-graph.md).

## `<specs.location>/`

The local download path declared in `SpecsConfig.location`. After `swax init`
this directory holds a copy of the specifications from the remote repository.

- Parent directories are created as needed by `copy_specs`.
- Re-running `init` **overwrites** existing files (spec updates).
- The directory structure of the source repository is preserved.
- **Symlinks** in the clone are **not** dereferenced — copied as regular files.

## Cleanup behavior

- The temporary clone produced by `clone_specs` is **always cleaned up**, even
  on exception (context-manager semantics).
- `.swax/` itself is never deleted automatically — only its files are
  overwritten.

## See also

- [Configuration](../getting-started/configuration.md) — `.swax/config.yml` schema.
- [Traceability graph](traceability-graph.md) — `.swax/traceability.yml` schema.
- [Architecture / fs cell](../architecture/cells/fs.md) — `ensure_swax_dir`,
  `copy_specs`.
