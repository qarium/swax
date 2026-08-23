"""Tests for build_incremental_graph_user_prompt.

Covers the full revision payload of the user prompt: current graph, change
set, new-specs content, the computed sorted universe, the closing
instruction, and the serialization of non-JSON-native scalars.
"""

import datetime

from swax.prompts import build_incremental_graph_user_prompt


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
