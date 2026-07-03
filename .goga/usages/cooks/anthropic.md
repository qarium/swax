# Anthropic — Claude API Client

## Domain

Patterns for calling the Claude API through the official `anthropic` Python SDK with a custom base URL. Target audience: the `llm/` cell and the `discover` command's graph-building step.

Swax uses `SWAX_LLM_PROTOCOL=anthropic`, `SWAX_LLM_BASE_URL`, and `SWAX_LLM_TOKEN` environment variables to configure the client. The base URL must NOT include a version path (e.g. `/v1`) — the SDK appends it.

---

## Client Construction

Read environment variables and construct the SDK client. The token and base URL come from configuration; never hardcode them.

```python
import os

from anthropic import Anthropic


def build_client() -> Anthropic:
    return Anthropic(
        api_key=os.environ["SWAX_LLM_TOKEN"],
        base_url=os.environ["SWAX_LLM_BASE_URL"],
    )
```

If `SWAX_LLM_TOKEN` is missing, raise a domain exception before constructing the client — fail fast with a clear message.

---

## Synchronous Chat Call

Use `messages.create` for single-shot inference. In swax the model identifier is supplied by the caller (the LLM cell reads it from `SWAX_LLM_MODEL` and injects it into `AnthropicAdapter`); the SDK cookbook below pins a literal for clarity.

```python
DEFAULT_MODEL = "claude-sonnet-4-6"


def ask(client: Anthropic, system: str, user: str) -> str:
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
```

---

## Structured Output

For dependency inference, request JSON output explicitly and parse defensively.

```python
import json


def infer_dependencies(client: Anthropic, system: str, endpoints: list[str]) -> dict[str, list[str]]:
    user_payload = json.dumps({"endpoints": endpoints})
    raw = ask(client, system=system, user=user_payload)
    parsed = json.loads(raw)
    return {k: list(v) for k, v in parsed.items()}
```

Catch `json.JSONDecodeError` and surface as a domain exception — the LLM may return prose around the JSON.

---

## Multi-turn Clarification

The `discover` command performs two passes: (1) propose dependencies, (2) ask for schemas of ambiguous pairs to refine. Use a multi-turn `messages` array.

```python
def refine_with_schemas(
    client: Anthropic,
    system: str,
    initial_user: str,
    followup_with_schemas: str,
) -> str:
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=4096,
        system=system,
        messages=[
            {"role": "user", "content": initial_user},
            {"role": "assistant", "content": "Clarify ambiguous pairs."},
            {"role": "user", "content": followup_with_schemas},
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")
```

---

## Error Handling

Wrap API errors in a domain exception. Retry policy belongs in the service layer, not in client construction.

```python
from anthropic import APIError, RateLimitError


def call_or_raise(client: Anthropic, **kwargs):
    try:
        return client.messages.create(**kwargs)
    except RateLimitError as exc:
        raise LLMRateLimitedError(reason=str(exc)) from exc
    except APIError as exc:
        raise LLMCallError(reason=str(exc)) from exc
```

---

## Testing

Mock the SDK client at the import point. Do not call the live API in tests.

```python
def test_infer_dependencies_returns_mapping(mocker) -> None:
    client = mocker.MagicMock(spec=Anthropic)
    client.messages.create.return_value.content = [mocker.MagicMock(text='{"a": ["b"]}', type="text")]
    result = infer_dependencies(client, system="sys", endpoints=["a", "b"])
    assert result == {"a": ["b"]}
```