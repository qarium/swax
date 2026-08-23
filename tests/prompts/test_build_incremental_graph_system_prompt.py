"""Tests for build_incremental_graph_system_prompt.

Covers the five contract fragments pinned in the constant system prompt: the
revising-analyst role, the full-graph output contract, the universe
restriction, the JSON-only rule, and the paths-only rule.
"""

from swax.prompts import build_incremental_graph_system_prompt


class TestBuildIncrementalSystemPrompt:
    def test_build_incremental_system_prompt_pins_contract_fragments(self):
        prompt = build_incremental_graph_system_prompt()

        assert "revising an existing dependency graph" in prompt
        assert "complete updated graph, not a delta" in prompt
        assert "do not include paths outside it" in prompt
        assert "parseable as JSON" in prompt
        assert "paths only, not HTTP methods" in prompt
