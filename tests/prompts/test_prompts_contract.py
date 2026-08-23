"""Contract tests for the swax.prompts cell.

These tests pin the public surface and signatures of the prompt-builder
routines. The original three fail with ImportError until the modules and the
facade re-exports exist (task 11); the two incremental-graph builders were
appended by the update feature (task 6 of add-update-command).
"""

import inspect

from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
    build_incremental_graph_system_prompt,
    build_incremental_graph_user_prompt,
    build_refine_user_prompt,
)


class TestPromptsContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(build_graph_system_prompt)
        assert callable(build_graph_user_prompt)
        assert callable(build_refine_user_prompt)

    def test_build_graph_system_prompt_signature(self):
        signature = inspect.signature(build_graph_system_prompt)

        assert list(signature.parameters) == []
        assert signature.return_annotation is str

    def test_build_graph_user_prompt_signature(self):
        signature = inspect.signature(build_graph_user_prompt)

        assert list(signature.parameters) == ["endpoints"]
        assert signature.parameters["endpoints"].annotation == list[str]
        assert signature.return_annotation is str

    def test_build_refine_user_prompt_signature(self):
        signature = inspect.signature(build_refine_user_prompt)

        assert list(signature.parameters) == ["ambiguous_pairs", "schemas"]
        assert signature.parameters["ambiguous_pairs"].annotation == list[str]
        assert signature.parameters["schemas"].annotation is dict
        assert signature.return_annotation is str


class TestIncrementalGraphPromptsContract:
    def test_routines_are_importable_from_facade(self):
        assert callable(build_incremental_graph_system_prompt)
        assert callable(build_incremental_graph_user_prompt)

    def test_build_incremental_graph_system_prompt_signature(self):
        signature = inspect.signature(build_incremental_graph_system_prompt)

        assert list(signature.parameters) == []
        assert signature.return_annotation is str

    def test_build_incremental_graph_user_prompt_signature(self):
        signature = inspect.signature(build_incremental_graph_user_prompt)

        assert list(signature.parameters) == [
            "existing_edges",
            "diff_added",
            "diff_removed",
            "diff_modified",
            "added_endpoints",
            "added_schemas",
        ]
        assert signature.parameters["existing_edges"].annotation == dict[str, list[str]]
        assert signature.parameters["diff_added"].annotation == list[str]
        assert signature.parameters["diff_removed"].annotation == list[str]
        assert signature.parameters["diff_modified"].annotation == dict[str, list[str]]
        assert signature.parameters["added_endpoints"].annotation == list[str]
        assert signature.parameters["added_schemas"].annotation is dict
        assert signature.return_annotation is str
