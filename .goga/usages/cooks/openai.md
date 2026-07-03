# OpenAI — Chat Completions Client

## Domain

Patterns for calling the OpenAI-compatible Chat Completions API through the official `openai` Python SDK with a custom base URL. Target audience: the `llm/` cell and the `discover` command.

Swax uses `SWAX_LLM_PROTOCOL=openai`, `SWAX_LLM_BASE_URL`, and `SWAX_LLM_TOKEN` environment variables to configure the client. The base URL must NOT include a version path (e.g. `/v1`) — the SDK appends it.

The provider interface must mirror the Anthropic client (see `anthropic.md`) so the rest of the system can switch providers via env var without code changes.

---

## Client Construction

```python
import os

from openai import OpenAI


def build_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["SWAX_LLM_TOKEN"],
        base_url=os.environ["SWAX_LLM_BASE_URL"],
    )
```

---

## Synchronous Chat Call

In swax the model identifier is supplied by the caller (the LLM cell reads it from `SWAX_LLM_MODEL` and injects it into `OpenAIAdapter`); the SDK cookbook below pins a literal for clarity.

```python
DEFAULT_MODEL = "gpt-4o"


def ask(client: OpenAI, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""
```

---

## Structured Output

For dependency inference, request JSON and parse defensively — same pattern as the Anthropic client.

```python
import json


def infer_dependencies(client: OpenAI, system: str, endpoints: list[str]) -> dict[str, list[str]]:
    user_payload = json.dumps({"endpoints": endpoints})
    raw = ask(client, system=system, user=user_payload)
    parsed = json.loads(raw)
    return {k: list(v) for k, v in parsed.items()}
```

---

## Multi-turn Clarification

```python
def refine_with_schemas(
    client: OpenAI,
    system: str,
    initial_user: str,
    followup_with_schemas: str,
) -> str:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": initial_user},
            {"role": "assistant", "content": "Clarify ambiguous pairs."},
            {"role": "user", "content": followup_with_schemas},
        ],
    )
    return response.choices[0].message.content or ""
```

---

## Error Handling

Mirror the Anthropic client's domain exceptions.

```python
from openai import APIError, RateLimitError


def call_or_raise(client: OpenAI, **kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except RateLimitError as exc:
        raise LLMRateLimitedError(reason=str(exc)) from exc
    except APIError as exc:
        raise LLMCallError(reason=str(exc)) from exc
```

---

## Provider Abstraction

Both Anthropic and OpenAI clients must satisfy a shared protocol so the application layer is provider-agnostic:

```python
import typing


class LLMClient(typing.Protocol):
    def ask(self, system: str, user: str) -> str: ...
    def infer_dependencies(self, system: str, endpoints: list[str]) -> dict[str, list[str]]: ...
```

The factory selects the implementation based on `SWAX_LLM_PROTOCOL`:

```python
def build_llm_client() -> LLMClient:
    protocol = os.environ["SWAX_LLM_PROTOCOL"]
    if protocol == "anthropic":
        return AnthropicAdapter(build_anthropic_client())
    if protocol == "openai":
        return OpenAIAdapter(build_openai_client())
    raise UnsupportedLLMProtocolError(protocol=protocol)
```

---

## Testing

Mock the SDK client at the import point. Same pattern as Anthropic tests.