"""Logic tests for the incremental-graph prompt builders.

Tests cover the five contract fragments pinned in the system prompt and the
full revision payload of the user prompt: current graph, change set, new-specs
content, the computed sorted universe, and the closing instruction.
"""

import datetime

from swax.prompts import (
    build_incremental_graph_system_prompt,
    build_incremental_graph_user_prompt,
)


class TestBuildIncrementalSystemPrompt:
    def test_build_incremental_system_prompt_pins_contract_fragments(self):
        prompt = build_incremental_graph_system_prompt()

        assert "revising an existing dependency graph" in prompt
        assert "complete updated graph, not a delta" in prompt
        assert "do not include paths outside it" in prompt
        assert "parseable as JSON" in prompt
        assert "paths only, not HTTP methods" in prompt


class TestBuildIncrementalUserPrompt:
    def test_build_incremental_user_prompt_renders_all_sections(self):
        prompt = build_incremental_graph_user_prompt(
            existing_edges={"/users": ["/orders"]},
            diff_added=["/billing"],
            diff_removed=["/legacy"],
            diff_modified={"/users": ["get responses 200 changed"]},
            added_endpoints=["/admin"],
            added_schemas={"Admin": {"type": "object"}},
        )

        assert '"/users": ["/orders"]' in prompt
        assert '"/billing"' in prompt
        assert '"/legacy"' in prompt
        assert '"modified"' in prompt
        assert "get responses 200 changed" in prompt
        assert '"/admin"' in prompt
        assert "Admin" in prompt
        assert '["/admin", "/billing", "/users"]' in prompt
        assert "covering exactly every endpoint" in prompt

    def test_build_incremental_user_prompt_serializes_non_json_scalars(self):
        # Parsed YAML carries non-JSON-native scalars (an unquoted date becomes
        # datetime.date) — the payload renders them instead of raising.
        prompt = build_incremental_graph_user_prompt(
            existing_edges={},
            diff_added=[],
            diff_removed=[],
            diff_modified={},
            added_endpoints=["/billing"],
            added_schemas={"Billing": {"properties": {"created": {"example": datetime.date(2024, 1, 31)}}}},
        )

        assert "2024-01-31" in prompt
