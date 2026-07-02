"""Contract tests for the swax.prompts cell.

These tests pin the public surface and signatures of the three prompt-builder
routines. They fail with ImportError until the modules and the facade
re-exports exist (task 11).
"""

import inspect

from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
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
