"""Logic tests for the impact-report prompt builders.

Tests cover the constant system prompt's contract markers and constraints, the
five-primitive payload in the user prompt, determinism for identical input
(including sort_keys for the dict-typed arguments), and the absence of secret
markers beyond the data passed as arguments.
"""

from swax.prompts import (
    build_impact_report_system_prompt,
    build_impact_report_user_prompt,
)


class TestImpactReportSystemPrompt:
    def test_system_prompt_mentions_contract_markers(self):
        prompt = build_impact_report_system_prompt()

        assert "impact analyst" in prompt.lower()
        assert "summary" in prompt
        assert "risk" in prompt
        assert "modified" in prompt
        assert "affected" in prompt
        assert "requirements" in prompt
        assert "checklist" in prompt
        assert "HIGH" in prompt
        assert "MEDIUM" in prompt
        assert "LOW" in prompt

    def test_system_prompt_forbids_prose(self):
        prompt = build_impact_report_system_prompt()

        assert "no prose" in prompt.lower() or "json only" in prompt.lower()

    def test_system_prompt_is_constant(self):
        first = build_impact_report_system_prompt()
        second = build_impact_report_system_prompt()

        assert first == second


class TestImpactReportUserPrompt:
    def test_user_prompt_includes_all_data(self):
        prompt = build_impact_report_user_prompt(["/x"], [], {"/y": ["resp 200 changed"]}, ["/z"], {"/z": ["/w"]})

        assert "/x" in prompt
        assert "/y" in prompt
        assert "/z" in prompt
        assert "/w" in prompt

    def test_user_prompt_is_deterministic_for_same_input(self):
        args = (
            ["/x"],
            ["/y"],
            {"/a": ["resp 200 changed"], "/b": ["param changed"]},
            ["/z"],
            {"/z": ["/w"], "/a": ["/q"]},
        )

        assert build_impact_report_user_prompt(*args) == build_impact_report_user_prompt(*args)

    def test_user_prompt_sorts_dict_keys_deterministically(self):
        # Different insertion order of dict-typed args must yield identical
        # output — proves sort_keys=True for modified and graph_context.
        first = build_impact_report_user_prompt([], [], {"/b": ["x"], "/a": ["y"]}, [], {"/d": ["/e"], "/c": []})
        second = build_impact_report_user_prompt([], [], {"/a": ["y"], "/b": ["x"]}, [], {"/c": [], "/d": ["/e"]})

        assert first == second

    def test_user_prompt_does_not_embed_secrets(self):
        prompt = build_impact_report_user_prompt([], [], {}, [], {})

        assert "SWAX_LLM_TOKEN" not in prompt
