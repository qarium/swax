"""Contract tests for the impact-report prompt builders.

These tests pin the public surface and signatures of the two impact-report
prompt-builder routines. They fail with ImportError until the modules and the
facade re-exports exist (task 4).
"""

import inspect

from swax.prompts import (
    build_impact_report_system_prompt,
    build_impact_report_user_prompt,
)


class TestImpactReportPromptsContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(build_impact_report_system_prompt)
        assert callable(build_impact_report_user_prompt)

    def test_build_impact_report_system_prompt_signature(self):
        signature = inspect.signature(build_impact_report_system_prompt)

        assert list(signature.parameters) == []
        assert signature.return_annotation is str

    def test_build_impact_report_user_prompt_signature(self):
        signature = inspect.signature(build_impact_report_user_prompt)

        assert list(signature.parameters) == [
            "added",
            "removed",
            "modified",
            "affected",
            "graph_context",
        ]
        assert signature.parameters["added"].annotation == list[str]
        assert signature.parameters["removed"].annotation == list[str]
        assert signature.parameters["modified"].annotation == dict[str, list[str]]
        assert signature.parameters["affected"].annotation == list[str]
        assert signature.parameters["graph_context"].annotation == dict[str, list[str]]
        assert signature.return_annotation is str
