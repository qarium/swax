"""Contract tests for the swax.git cell.

These tests pin the public surface and signatures of clone_specs and the two
domain errors. They fail with ImportError until the routines, errors, and the
facade re-exports exist (task 8).
"""

import contextlib
import inspect
import pathlib

import pytest
from swax.git import RepositoryCloneError, SpecsNotFoundError, clone_specs


class TestGitContract:
    def test_entities_are_importable_from_facade(self):
        assert callable(clone_specs)
        assert issubclass(RepositoryCloneError, Exception)
        assert issubclass(SpecsNotFoundError, Exception)

    def test_clone_specs_signature(self):
        signature = inspect.signature(clone_specs)

        assert list(signature.parameters) == ["repo_url", "specs_location"]
        assert signature.parameters["repo_url"].annotation is str
        assert signature.parameters["specs_location"].annotation is str

    def test_clone_specs_is_context_manager_factory(self, mocker):
        mocker.patch("swax.git.clone_specs.Repo.clone_from")

        context_manager = clone_specs("https://example.com/repo.git", "specs")

        assert isinstance(context_manager, contextlib.AbstractContextManager)

    def test_repository_clone_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            RepositoryCloneError("https://example.com/repo.git", "boom")

    def test_specs_not_found_error_is_keyword_only(self):
        with pytest.raises(TypeError):
            SpecsNotFoundError(pathlib.Path("/missing"))
