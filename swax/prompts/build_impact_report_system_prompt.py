"""System prompt for the API change impact analyst role.

build_impact_report_system_prompt returns the constant system message for the
single-turn run_plan scenario. It fixes the LLM role, the six-key JSON output
contract, the allowed risk values, and the prohibition of prose around JSON.
"""


def build_impact_report_system_prompt() -> str:
    """Return the constant system prompt for the impact analyst.

    Returns:
        The system message for the single-turn LLMClient.ask call in run_plan.
    """
    return (
        "You are an API change impact analyst.\n"
        "\n"
        "Assess the testing impact of the provided API endpoint changes.\n"
        "\n"
        "Output contract:\n"
        '- Return a JSON object with exactly six keys: "summary" (str), '
        '"risk" (str), "modified" (list[str]), "affected" (list[str]), '
        '"requirements" (list[str]), and "checklist" (list[str]).\n'
        '- "risk" must be one of: HIGH, MEDIUM, LOW.\n'
        "- JSON only — no prose, no code fences, no commentary. The response "
        "must be parseable as JSON."
    )


__all__: list[str] = [
    "build_impact_report_system_prompt",
]
