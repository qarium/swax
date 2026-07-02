"""Logic tests for the swax.git cell.

All tests mock Repo.clone_from at the import point (swax.git.clone_specs) — no
real network cloning happens. They cover the success path, the two domain
errors (GitCommandError mapping and missing specs subdirectory), and the
edge case guaranteeing the temporary directory is cleaned up on clone failure.
"""

import pathlib

import pytest
from git.exc import GitCommandError
from swax.git import RepositoryCloneError, SpecsNotFoundError, clone_specs

REPO_URL = "https://example.com/repo.git"


def _seed_specs(url, to_path, depth=1) -> None:
    """Create a specs subdirectory inside a cloned temp path (mock side effect)."""
    specs_dir = pathlib.Path(str(to_path)) / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "api.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")


class TestCloneSpecs:
    def test_clone_specs_yields_specs_path_on_success(self, mocker):
        mocker.patch("swax.git.clone_specs.Repo.clone_from", side_effect=_seed_specs)

        with clone_specs(REPO_URL, "specs") as specs_path:
            assert specs_path.name == "specs"
            assert (specs_path / "api.yaml").exists()

    def test_clone_specs_uses_shallow_clone(self, mocker):
        clone_from = mocker.patch("swax.git.clone_specs.Repo.clone_from", side_effect=_seed_specs)

        with clone_specs(REPO_URL, "specs"):
            pass

        assert clone_from.call_args.kwargs["depth"] == 1

    def test_clone_specs_raises_repository_clone_error_on_git_error(self, mocker):
        mocker.patch(
            "swax.git.clone_specs.Repo.clone_from",
            side_effect=GitCommandError("clone", "auth failed"),
        )

        with pytest.raises(RepositoryCloneError) as exc_info, clone_specs(REPO_URL, "specs"):
            pass

        assert exc_info.value.url == REPO_URL
        assert "auth failed" in exc_info.value.reason

    def test_clone_specs_raises_specs_not_found_when_subdir_missing(self, mocker):
        mocker.patch("swax.git.clone_specs.Repo.clone_from")

        with pytest.raises(SpecsNotFoundError) as exc_info, clone_specs(REPO_URL, "missing"):
            pass

        assert exc_info.value.path.name == "missing"

    def test_clone_specs_cleans_up_tempdir_on_clone_failure(self, mocker):
        captured: list[pathlib.Path] = []

        def fake_clone_from(url, to_path, depth=1):
            captured.append(pathlib.Path(str(to_path)))
            raise GitCommandError("clone", "auth failed")

        mocker.patch("swax.git.clone_specs.Repo.clone_from", side_effect=fake_clone_from)

        with pytest.raises(RepositoryCloneError), clone_specs(REPO_URL, "specs"):
            pass

        # TemporaryDirectory.__exit__ runs as the exception propagates, so the
        # temp directory must be removed from disk on every failure outcome.
        assert captured, "Repo.clone_from must be invoked"
        assert not captured[0].exists()
