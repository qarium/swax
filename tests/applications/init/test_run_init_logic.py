"""Logic tests for the swax.applications.init cell (task 16).

clone_specs and copy_specs are mocked at their use site
(swax.applications.init.run_init) so no real network clone or filesystem copy
runs. The three scenarios verify the core contract — config is persisted before
the clone runs, so a clone failure still leaves .swax/config.yml on disk — plus
that domain errors propagate uncaught.
"""

import contextlib
import pathlib

import pytest
from swax.applications.init import run_init
from swax.git import RepositoryCloneError, SpecsNotFoundError

REPO_URL = "https://example.com/repo.git"
SPECS_LOCATION = "specs/"
PATCH_CLONE = "swax.applications.init.run_init.clone_specs"
PATCH_COPY = "swax.applications.init.run_init.copy_specs"


class TestRunInit:
    def test_run_init_persists_config_then_copies_specs(self, tmp_path, mocker):
        cloned_specs = tmp_path / "cloned_specs"
        cloned_specs.mkdir()
        (cloned_specs / "api.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
        download_path = tmp_path / "local_specs"

        @contextlib.contextmanager
        def fake_clone(repo_url, specs_location):
            # Config must already be on disk before cloning starts.
            assert (tmp_path / ".swax" / "config.yml").exists()
            yield cloned_specs

        mock_clone = mocker.patch(PATCH_CLONE, side_effect=fake_clone)
        mock_copy = mocker.patch(PATCH_COPY)

        run_init(
            repo_url=REPO_URL,
            specs_location=SPECS_LOCATION,
            download_path=download_path,
            project_root=tmp_path,
        )

        assert (tmp_path / ".swax" / "config.yml").exists()
        mock_clone.assert_called_once_with(REPO_URL, SPECS_LOCATION)
        mock_copy.assert_called_once_with(source=cloned_specs, destination=download_path)

    def test_run_init_config_survives_clone_failure(self, tmp_path, mocker):
        mock_clone = mocker.patch(PATCH_CLONE)
        mock_clone.side_effect = RepositoryCloneError(url=REPO_URL, reason="auth failed")
        mock_copy = mocker.patch(PATCH_COPY)

        with pytest.raises(RepositoryCloneError):
            run_init(
                repo_url=REPO_URL,
                specs_location=SPECS_LOCATION,
                download_path=tmp_path / "local_specs",
                project_root=tmp_path,
            )

        assert (tmp_path / ".swax" / "config.yml").exists()
        content = (tmp_path / ".swax" / "config.yml").read_text(encoding="utf-8")
        assert REPO_URL in content
        mock_copy.assert_not_called()
        mock_clone.assert_called_once()

    def test_run_init_propagates_specs_not_found(self, tmp_path, mocker):
        missing_path = pathlib.Path("/nonexistent/specs")
        mock_clone = mocker.patch(PATCH_CLONE)
        mock_clone.side_effect = SpecsNotFoundError(path=missing_path)
        mocker.patch(PATCH_COPY)

        with pytest.raises(SpecsNotFoundError):
            run_init(
                repo_url=REPO_URL,
                specs_location=SPECS_LOCATION,
                download_path=tmp_path / "local_specs",
                project_root=tmp_path,
            )

        mock_clone.assert_called_once()
