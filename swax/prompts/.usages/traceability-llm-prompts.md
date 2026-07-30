# Traceability LLM prompts — assembling prompts for graph construction

## Domain

Templates for assembling prompts for the LLM-based API dependency analysis. Target audience: cell `applications/discover/` (uses three prompt builders in the two-pass traceability graph construction scenario).

The cell assembles prompt strings — the LLM calls and JSON parsing themselves are performed by the consumer via `LLMClient` (cell `llm/`). This is the separation of concerns: `prompts/` knows "what to say to the LLM", `llm/` knows "how to call the API".

---

## Analyst system prompt

`build_graph_system_prompt` returns a constant system prompt, reused in both passes:

```python
from swax.prompts import build_graph_system_prompt


def setup_llm_context() -> str:
    return build_graph_system_prompt()
```

Consumer conventions:
- Takes no parameters — the system prompt is constant for the `discover` use case.
- Passed as `system=` to `LLMClient.ask` / `ask_multi_turn`.
- Requests a JSON object `{source_path: [dependent_paths]}` without prose wrapping.

---

## First pass: dependency hypotheses

`build_graph_user_prompt` builds the user message with the full list of endpoints:

```python
from swax.prompts import build_graph_user_prompt


def first_pass(endpoints: list[str]) -> str:
    return build_graph_user_prompt(endpoints)
```

Consumer conventions:
- `endpoints` — API paths from `extract_paths` (cell `openapi/`), sorted.
- The LLM returns dependency hypotheses and may flag uncertain pairs for the refinement pass.
- The consumer parses the JSON defensively (via `json.loads` with `JSONDecodeError` handling).

---

## Refinement pass: schemas for ambiguous pairs

`build_refine_user_prompt` builds the user message for the second (multi-turn) turn — with schemas of the ambiguous pairs:

```python
from swax.prompts import build_refine_user_prompt


def refine_pass(ambiguous_pairs: list[str], schemas: dict) -> str:
    return build_refine_user_prompt(ambiguous_pairs, schemas)
```

Consumer conventions:
- `ambiguous_pairs` — pairs the LLM flagged as uncertain in the first pass (e.g., `"/users -> /orders"`).
- `schemas` — a dictionary of schemas from `extract_schemas` (cell `openapi/`).
- Used in `LLMClient.ask_multi_turn` — the multi-turn context already carries the first turn.
- The output JSON contract is identical to the first pass — the consumer reuses the same parser.

---

## Full two-pass scenario

The `run_discover` use case assembles all three prompts into a single scenario:

```python
from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
    build_refine_user_prompt,
)


def run_two_pass_analysis(endpoints, ambiguous_pairs, schemas, llm_client):
    system = build_graph_system_prompt()
    first_user = build_graph_user_prompt(endpoints)
    raw_first = llm_client.ask(system=system, user=first_user)
    # ... parse raw_first, collect ambiguous_pairs ...

    refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)
    raw_refined = llm_client.ask_multi_turn(
        system=system,
        messages=[
            {"role": "user", "content": first_user},
            {"role": "assistant", "content": raw_first},
            {"role": "user", "content": refine_user},
        ],
    )
    return raw_refined
```

The consumer manages LLM error mapping (`LLMCallError`, `LLMRateLimitedError`) and JSON parsing on its own — this is not the responsibility of the `prompts/` cell.
