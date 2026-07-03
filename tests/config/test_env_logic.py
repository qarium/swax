"""Logic tests for the swax.config env routines.

Covers the behavior of load_env (missing file, shell precedence), require_vars
(missing, whitespace-only, all-present — incl. SWAX_LLM_MODEL), parse_protocol
(accept/reject), and parse_base_url (version rejection, slash stripping).
Environment state is controlled via monkeypatch so no real .env file is required.
"""

import os

import pytest
from swax.config import (
    InvalidLLMBaseURLError,
    InvalidLLMProtocolError,
    MissingEnvironmentVariablesError,
    load_env,
    parse_base_url,
    parse_protocol,
    require_vars,
)

REQUIRED_VARS = ("SWAX_LLM_MODEL", "SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN")


@pytest.fixture(autouse=True)
def _clean_swax_env(monkeypatch):
    """Ensure a deterministic environment for every test in this module."""
    for name in REQUIRED_VARS:
        monkeypatch.delenv(name, raising=False)


def _set_all_swax_vars(monkeypatch, **overrides):
    """Set all four mandatory SWAX_LLM_* vars; tests override what they need."""
    defaults = {
        "SWAX_LLM_MODEL": "claude-test-model",
        "SWAX_LLM_PROTOCOL": "anthropic",
        "SWAX_LLM_BASE_URL": "https://example.com",
        "SWAX_LLM_TOKEN": "tok",
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setenv(name, value)


class TestLoadEnv:
    def test_load_env_silent_on_missing_file(self, tmp_path):
        # A non-existent .env must not raise.
        load_env(tmp_path / ".env")

    def test_load_env_does_not_override_shell_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SWAX_LLM_TOKEN", "shell")
        env_file = tmp_path / ".env"
        env_file.write_text("SWAX_LLM_TOKEN=fromfile\n", encoding="utf-8")

        load_env(env_file)

        assert os.environ["SWAX_LLM_TOKEN"] == "shell"

    def test_load_env_loads_file_value_when_shell_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SWAX_LLM_TOKEN", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("SWAX_LLM_TOKEN=fromfile\n", encoding="utf-8")

        load_env(env_file)

        assert os.environ["SWAX_LLM_TOKEN"] == "fromfile"


class TestRequireVars:
    def test_require_vars_raises_on_missing_token(self, monkeypatch):
        _set_all_swax_vars(monkeypatch)
        monkeypatch.delenv("SWAX_LLM_TOKEN", raising=False)

        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            require_vars()

        assert "SWAX_LLM_TOKEN" in exc_info.value.missing

    def test_require_vars_raises_on_missing_model(self, monkeypatch):
        _set_all_swax_vars(monkeypatch)
        monkeypatch.delenv("SWAX_LLM_MODEL", raising=False)

        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            require_vars()

        assert "SWAX_LLM_MODEL" in exc_info.value.missing

    def test_require_vars_whitespace_only_is_missing(self, monkeypatch):
        _set_all_swax_vars(monkeypatch, SWAX_LLM_TOKEN="   ")

        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            require_vars()

        assert "SWAX_LLM_TOKEN" in exc_info.value.missing

    def test_require_vars_empty_string_is_missing(self, monkeypatch):
        _set_all_swax_vars(monkeypatch, SWAX_LLM_BASE_URL="")

        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            require_vars()

        assert "SWAX_LLM_BASE_URL" in exc_info.value.missing

    def test_require_vars_returns_mapping_when_all_present(self, monkeypatch):
        _set_all_swax_vars(monkeypatch)

        result = require_vars()

        assert result == {
            "SWAX_LLM_MODEL": "claude-test-model",
            "SWAX_LLM_PROTOCOL": "anthropic",
            "SWAX_LLM_BASE_URL": "https://example.com",
            "SWAX_LLM_TOKEN": "tok",
        }

    def test_require_vars_reports_all_missing_names(self):
        # Nothing set — all four must be reported.
        with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
            require_vars()

        assert sorted(exc_info.value.missing) == sorted(REQUIRED_VARS)


class TestParseProtocol:
    @pytest.mark.parametrize("value", ["anthropic", "openai"])
    def test_parse_protocol_accepts_supported_values(self, value):
        assert parse_protocol(value) == value

    def test_parse_protocol_rejects_unsupported(self):
        with pytest.raises(InvalidLLMProtocolError) as exc_info:
            parse_protocol("ftp")

        assert exc_info.value.value == "ftp"
        assert exc_info.value.allowed == ("anthropic", "openai")


class TestParseBaseUrl:
    @pytest.mark.parametrize("value", ["https://x.com/v1", "https://x.com/v2/", "https://x.com/v1/"])
    def test_parse_base_url_rejects_versioned_segments(self, value):
        with pytest.raises(InvalidLLMBaseURLError):
            parse_base_url(value)

    def test_parse_base_url_strips_trailing_slash(self):
        assert parse_base_url("https://x.com/") == "https://x.com"

    def test_parse_base_url_accepts_clean_url(self):
        assert parse_base_url("https://x.com") == "https://x.com"

    def test_parse_base_url_passes_offending_value_through(self):
        with pytest.raises(InvalidLLMBaseURLError) as exc_info:
            parse_base_url("https://x.com/v1")

        assert exc_info.value.value == "https://x.com/v1"
