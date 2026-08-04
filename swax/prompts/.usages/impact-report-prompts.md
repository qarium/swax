# Impact report prompts — single-turn LLM prompt assembly

## Domain

Prompt builders for the `plan` command's Impact Report. Target audience: cell `applications/plan/`.

## Assembly

```python
from swax.prompts import build_impact_report_system_prompt, build_impact_report_user_prompt

system = build_impact_report_system_prompt()
user = build_impact_report_user_prompt(added, removed, modified, affected, graph_context)
```

The system prompt fixes the role and the JSON output contract (risk ∈ {HIGH,MEDIUM,LOW}).
The user prompt carries only data as primitives — no paths/tokens/secrets are ever embedded.
