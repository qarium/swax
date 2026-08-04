"""Logic tests for render_impact_report (and the ImpactReport model wiring).

Verbatim from the design-doc Test Stack Trace
(`test_render_impact_report_no_change_renders_consistently`) plus additional
edge cases: non-empty report renders each section as a bullet list, checklist
items render as markdown checkboxes, and the render is deterministic with a
trailing newline.
"""

from swax.applications.plan.impact_report import ImpactReport
from swax.applications.plan.render_impact_report import render_impact_report


class TestRenderImpactReportLogic:
    def test_render_impact_report_no_change_renders_consistently(self):
        report = ImpactReport(
            summary="No changes detected",
            risk="LOW",
            modified=[],
            affected=[],
            requirements=[],
            checklist=[],
        )

        md = render_impact_report(report)

        assert "No changes detected" in md
        assert "LOW" in md
        assert "(none)" in md

    def test_render_impact_report_empty_sections_use_none_marker(self):
        report = ImpactReport(
            summary="No changes detected",
            risk="LOW",
            modified=[],
            affected=[],
            requirements=[],
            checklist=[],
        )

        md = render_impact_report(report)

        assert md.count("(none)") == 4
        assert md.endswith("\n")

    def test_render_impact_report_nonempty_report_has_section_headers_and_bullets(self):
        report = ImpactReport(
            summary="Checkout endpoint modified",
            risk="HIGH",
            modified=["/checkout"],
            affected=["/orders", "/payments"],
            requirements=["Re-run payment integration suite"],
            checklist=["Verify /checkout returns 200", "Check idempotency keys"],
        )

        md = render_impact_report(report)

        assert "# Impact Report" in md
        assert "**Summary:** Checkout endpoint modified" in md
        assert "**Risk:** HIGH" in md
        assert "## Modified Endpoints" in md
        assert "- /checkout" in md
        assert "## Affected Endpoints" in md
        assert "- /orders" in md
        assert "- /payments" in md
        assert "## Requirements" in md
        assert "- Re-run payment integration suite" in md
        assert "## Checklist" in md
        assert "- [ ] Verify /checkout returns 200" in md
        assert "- [ ] Check idempotency keys" in md

    def test_render_impact_report_is_deterministic(self):
        report = ImpactReport(
            summary="Some change",
            risk="MEDIUM",
            modified=["/users"],
            affected=["/orders"],
            requirements=["Verify auth"],
            checklist=["Run smoke tests"],
        )

        first = render_impact_report(report)
        second = render_impact_report(report)

        assert first == second
        assert first.endswith("\n")

    def test_render_impact_report_does_not_synthesize_content(self):
        report = ImpactReport(
            summary="No changes detected",
            risk="LOW",
            modified=[],
            affected=[],
            requirements=[],
            checklist=[],
        )

        md = render_impact_report(report)

        assert "- [ ]" not in md
        assert "SWAX_LLM_TOKEN" not in md

    def test_render_impact_report_partial_sections(self):
        report = ImpactReport(
            summary="Mixed change",
            risk="MEDIUM",
            modified=["/users"],
            affected=[],
            requirements=[],
            checklist=["Run suite"],
        )

        md = render_impact_report(report)

        assert "- /users" in md
        assert "## Affected Endpoints" in md
        assert md.count("(none)") == 2
        assert "- [ ] Run suite" in md
