"""Logic tests for the swax.prompts cell.

Tests cover the three prompt builders: the constant system prompt's role and
constraints, the endpoints payload in the first-pass user prompt, the
ambiguous-pairs/schemas payload in the refine prompt, and the determinism of
every routine for identical input.
"""

import datetime

import pytest
from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
    build_refine_user_prompt,
)


class TestGraphSystemPrompt:
    def test_system_prompt_mentions_role_and_constraints(self):
        prompt = build_graph_system_prompt()

        assert "dependency" in prompt.lower()
        assert "JSON" in prompt
        assert "paths only" in prompt.lower()
        # Explicit forbidding of prose around the JSON output.
        assert "no prose" in prompt.lower() or "json only" in prompt.lower()
        # Explicit statement that the graph ignores HTTP methods.
        assert "method" in prompt.lower()

    def test_system_prompt_takes_no_arguments_and_is_constant(self):
        first = build_graph_system_prompt()
        second = build_graph_system_prompt()

        assert first == second


class TestGraphUserPrompt:
    def test_user_prompt_includes_endpoints_payload(self):
        prompt = build_graph_user_prompt(["/a", "/b"])

        assert "/a" in prompt
        assert "/b" in prompt

    def test_user_prompt_states_two_keys_contract(self):
        prompt = build_graph_user_prompt(["/a"])

        assert "dependencies" in prompt
        assert "uncertain" in prompt

    def test_user_prompt_is_deterministic_for_same_input(self):
        assert build_graph_user_prompt(["/a", "/b"]) == build_graph_user_prompt(["/a", "/b"])


class TestRefineUserPrompt:
    def test_refine_prompt_includes_pairs_and_schemas(self):
        prompt = build_refine_user_prompt(["/a -> /b"], {"User": {"type": "object"}})

        assert "/a -> /b" in prompt
        assert "User" in prompt

    def test_refine_prompt_forbids_external_paths(self):
        prompt = build_refine_user_prompt([], {})

        assert "Do not introduce paths" in prompt

    def test_refine_prompt_serializes_non_json_scalars(self):
        # Parsed YAML carries non-JSON-native scalars (an unquoted date becomes
        # datetime.date) — the payload renders them instead of raising.
        prompt = build_refine_user_prompt([], {"Billing": {"example": datetime.date(2024, 1, 31)}})

        assert "2024-01-31" in prompt

    @pytest.mark.parametrize(("pairs", "schemas"), [([], {}), (["/a -> /b"], {"User": {}})])
    def test_refine_prompt_is_deterministic_for_same_input(self, pairs, schemas):
        assert build_refine_user_prompt(pairs, schemas) == build_refine_user_prompt(pairs, schemas)
