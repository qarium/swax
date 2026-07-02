"""Logic tests for the swax.config storage routines.

Covers load_config (valid YAML parsing) and save_config (parent directory
creation, deterministic YAML output, idempotent re-write) plus a full
save -> load round-trip. All filesystem operations use tmp_path.
"""

from swax.config import (
    Config,
    GitConfig,
    SpecsConfig,
    load_config,
    save_config,
)


def _make_config() -> Config:
    return Config(
        git=GitConfig(url="https://example.com/repo.git", location="specs/"),
        specs=SpecsConfig(type="openapi", location="local_specs/"),
    )


class TestStorageLogic:
    def test_load_config_parses_valid_yaml(self, tmp_path):
        path = tmp_path / ".swax" / "config.yml"
        path.parent.mkdir(parents=True)
        path.write_text(
            """\
git:
  url: https://example.com/repo.git
  location: specs/
specs:
  type: openapi
  location: local_specs/
""",
            encoding="utf-8",
        )

        config = load_config(path)

        assert config.git.url == "https://example.com/repo.git"
        assert config.git.location == "specs/"
        assert config.specs.type == "openapi"
        assert config.specs.location == "local_specs/"

    def test_save_config_creates_parents_and_writes_deterministic_yaml(self, tmp_path):
        config = Config(
            git=GitConfig(url="u", location="l"),
            specs=SpecsConfig(type="openapi", location="loc"),
        )
        path = tmp_path / ".swax" / "config.yml"

        save_config(config, path)

        assert path.exists()
        assert path.parent == tmp_path / ".swax"
        content = path.read_text(encoding="utf-8")
        assert "url: u" in content
        assert "type: openapi" in content
        # deterministic: re-writing yields a byte-identical file
        save_config(config, path)
        assert path.read_text(encoding="utf-8") == content

    def test_save_config_preserves_declaration_order(self, tmp_path):
        # sort_keys=False keeps declaration order (git before specs).
        path = tmp_path / "config.yml"
        save_config(_make_config(), path)
        content = path.read_text(encoding="utf-8")

        assert content.index("git:") < content.index("specs:")

    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "config.yml"
        original = _make_config()

        save_config(original, path)
        loaded = load_config(path)

        assert loaded == original

    def test_save_config_overwrites_existing_file(self, tmp_path):
        # Re-saving an updated config replaces the previous content.
        path = tmp_path / "config.yml"
        save_config(_make_config(), path)

        updated = Config(
            git=GitConfig(url="https://example.com/other.git", location="v2/"),
            specs=SpecsConfig(type="swagger", location="other_specs/"),
        )
        save_config(updated, path)

        loaded = load_config(path)
        assert loaded == updated
        assert loaded.git.url == "https://example.com/other.git"
