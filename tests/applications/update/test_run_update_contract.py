"""Contract tests for run_update (task 10).

Pins the public surface of the update transaction orchestrator: run_update is
importable from the swax.applications.update facade, its signature is
(project_root: pathlib.Path) -> str, the domain error stays importable, and
the facade exposes exactly the two-name final surface
["GraphRebuildFailedError", "run_update"].
"""

import inspect
import pathlib

import swax.applications.update as update_facade
from swax.applications.update import GraphRebuildFailedError, run_update


class TestRunUpdateContract:
    def test_importable_from_facade(self):
        assert callable(run_update)

    def test_domain_error_still_importable_from_facade(self):
        assert issubclass(GraphRebuildFailedError, Exception)

    def test_signature(self):
        signature = inspect.signature(run_update)

        parameters = list(signature.parameters)
        assert parameters == ["project_root"]
        assert signature.parameters["project_root"].annotation is pathlib.Path
        assert signature.return_annotation is str

    def test_facade_all_is_final_two_name_surface(self):
        assert update_facade.__all__ == ["GraphRebuildFailedError", "run_update"]
