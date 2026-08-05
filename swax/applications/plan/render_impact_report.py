"""Render an ImpactReport into the Markdown Impact Report template.

Pure transformation — no I/O and no LLM calls. The template is fixed: a title,
a Summary/Risk pair, and four sections (Modified Endpoints, Affected
Endpoints, Requirements, Checklist). Empty list sections render as
"- (none)" so the section is always present and unambiguous. The no-change
report renders identically to any other.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .impact_report import ImpactReport


def _render_bullets(items: list[str]) -> str:
    """Render a list of strings as Markdown bullets, or a single "(none)".

    Args:
        items: the items to render.

    Returns:
        A bullet list joined by newlines, or "- (none)" when items is empty.
    """
    if not items:
        return "- (none)"
    return "\n".join(f"- {item}" for item in items)


def render_impact_report(report: "ImpactReport") -> str:
    """Render an ImpactReport as the Markdown Impact Report.

    The render is pure: every line is derived from report fields only. Empty
    list sections are rendered as "- (none)". The returned string ends with a
    trailing newline.

    Args:
        report: the impact report model (LLM-generated or the no-change
            placeholder).

    Returns:
        The Impact Report as Markdown following the fixed template.
    """
    sections = [
        "# Impact Report",
        "",
        "## Summary",
        f"**Risk:** {report.risk}",
        "",
        f"{report.summary}",
        "",
        "## Modified Endpoints",
        _render_bullets(report.modified),
        "",
        "## Affected Endpoints",
        _render_bullets(report.affected),
        "",
        "## Requirements",
        _render_bullets(report.requirements),
        "",
        "## Checklist",
        "\n".join(f"- [ ] {item}" for item in report.checklist) or "- (none)",
    ]
    return "\n".join(sections) + "\n"


__all__: list[str] = [
    "render_impact_report",
]
