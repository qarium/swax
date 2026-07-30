# Project layout — `.swax/` directory and spec copying

## Domain

Templates for managing the Swax project file structure. Target audience: cell `applications/init/` (creates the structure and copies specifications after cloning).

The Swax project layout on the filesystem:
```
<project_root>/
├── .swax/
│   ├── config.yml          # created via save_config
│   └── traceability.yml    # created later via save_traceability
└── <specs.location>/       # specifications land here via copy_specs
    └── *.yaml | *.json
```

---

## Guaranteeing the `.swax/` directory

Call before every write to `.swax/` — idempotent:

```python
from pathlib import Path

from swax.fs import ensure_swax_dir


def write_config(project_root: Path) -> Path:
    swax_dir = ensure_swax_dir(project_root)
    config_path = swax_dir / "config.yml"
    # save_config(config, config_path) — delegated to the `config/` cell
    return config_path
```

`ensure_swax_dir` creates `.swax/` with `parents=True, exist_ok=True` — safe to call repeatedly.

---

## Copying specifications

After cloning the repository via `clone_specs` (cell `git/`), the specifications must be moved to the local project path. The destination path is taken from `SpecsConfig.location`:

```python
from pathlib import Path

from swax.fs import copy_specs


def install_specs(specs_in_clone: Path, download_path: Path) -> None:
    copy_specs(source=specs_in_clone, destination=download_path)
```

Consumer conventions:
- `source` — path yielded by `clone_specs` (the temporary clone directory).
- `destination` — local path from `SpecsConfig.location`. The `fs/` cell creates parent directories as needed.
- Re-running `init` overwrites existing files (updating the local specifications).
