"""Contract tests for the ImpactReport model and render_impact_report.

These tests pin the public surface and signatures of the plan use-case
foundation: module-level import paths, keyword-only construction of
ImpactReport, the six accessible fields, and render_impact_report accepting an
ImpactReport and returning a str. They fail with ImportError until the modules
exist (task 5).
"""

import inspect

import pytest
from pydantic import BaseModel
from swax.applications.plan.impact_report import ImpactReport
from swax.applications.plan.render_impact_report import render_impact_report


class TestImpactReportContract:
    def test_impact_report_is_importable_from_module(self):
        assert isinstance(ImpactReport, type)

    def test_impact_report_is_keyword_only(self):
        with pytest.raises(TypeError):
            ImpactReport("summary", "LOW", [], [], [], [])

    def test_impact_report_exposes_six_fields(self):
        report = ImpactReport(
            summary="Some change",
            risk="MEDIUM",
            modified=["/users"],
            affected=["/orders"],
            requirements=["Verify auth"],
            checklist=["Run smoke tests"],
        )

        assert report.summary == "Some change"
        assert report.risk == "MEDIUM"
        assert report.modified == ["/users"]
        assert report.affected == ["/orders"]
        assert report.requirements == ["Verify auth"]
        assert report.checklist == ["Run smoke tests"]

    def test_impact_report_defines_no_custom_methods(self):
        own_callables = {
            name for name, value in vars(ImpactReport).items() if callable(value) and name not in vars(BaseModel)
        }

        assert own_callables == set()


class TestRenderImpactReportContract:
    def test_render_impact_report_is_callable(self):
        assert callable(render_impact_report)

    def test_render_impact_report_signature(self):
        signature = inspect.signature(render_impact_report)

        params = list(signature.parameters)
        assert params == ["report"]
        assert signature.return_annotation is str

    def test_render_returns_string(self):
        report = ImpactReport(summary="s", risk="LOW", modified=[], affected=[], requirements=[], checklist=[])

        rendered = render_impact_report(report)

        assert isinstance(rendered, str)
