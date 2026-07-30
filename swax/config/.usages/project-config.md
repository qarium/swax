# Project configuration — `.swax/config.yml`

## Domain

Templates for reading and writing the Swax project configuration. Target audience: cells `applications/init/` (writes the config after the interactive survey) and `applications/discover/` (reads the config for paths to the specifications).

The configuration is stored in YAML and describes the git repository with the specifications and the local path where they are saved.

---

## Model

```python
from swax.config import Config, GitConfig, SpecsConfig

config = Config(
    git=GitConfig(url="https://github.com/org/api-specs.git", location="specs/"),
    specs=SpecsConfig(type="openapi", location="specs/"),
)
```

The `specs.type` field declares the format (`"swagger"` or `"openapi"`); the actual parser (Prance) determines the version automatically, so the value is informational.

---

## Saving after initialization

`run_init` builds the configuration from the user's answers and saves it:

```python
from pathlib import Path

from swax.config import Config, GitConfig, SpecsConfig, save_config


def persist_config(repo_url: str, specs_location: str, download_path: Path, project_root: Path) -> None:
    config = Config(
        git=GitConfig(url=repo_url, location=specs_location),
        specs=SpecsConfig(type="openapi", location=str(download_path)),
    )
    save_config(config, project_root / ".swax" / "config.yml")
```

`save_config` creates parent directories and writes deterministic YAML — the diff between runs is stable.

---

## Reading before graph construction

`run_discover` reads the configuration to find where the local specifications live:

```python
from swax.config import load_config


def locate_specs(project_root: Path) -> Path:
    config = load_config(project_root / ".swax" / "config.yml")
    return project_root / config.specs.location
```

The configuration file must exist by the time `discover` runs — `init` must have been run previously.
