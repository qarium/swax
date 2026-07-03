"""Storage routines: YAML (de)serialization of Config.

load_config reads a UTF-8 YAML file and validates it into a Config via
pydantic. save_config dumps Config to deterministic YAML (sort_keys=False,
allow_unicode=True, default_flow_style=False) and creates parent
directories so the output reads cleanly in diffs. Both operate on
pathlib.Path values.
"""

import pathlib

import yaml

from .config import Config


def load_config(path: pathlib.Path) -> Config:
    """Read and validate a YAML config file into a Config model.

    Args:
        path: location of the YAML file (e.g. .swax/config.yml).

    The raw YAML is parsed with yaml.safe_load and validated through
    Config.model_validate, so malformed or schema-violating files raise
    pydantic's ValidationError.
    """
    raw_text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(raw_text)
    return Config.model_validate(raw)


def save_config(config: Config, path: pathlib.Path) -> None:
    """Persist a Config to a YAML file with deterministic formatting.

    Args:
        config: the Config instance to serialize.
        path: destination file path; parent directories are created.

    The dump uses sort_keys=False (declaration order preserved),
    allow_unicode=True, and default_flow_style=False so repeated writes
    produce byte-identical files.
    """
    payload = config.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    path.write_text(yaml_text, encoding="utf-8")


__all__: list[str] = [
    "load_config",
    "save_config",
]
