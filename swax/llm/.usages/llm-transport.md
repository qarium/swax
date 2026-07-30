# LLM transport — provider-agnostic access to the LLM API

## Domain

Templates for working with the LLM client: factory by `SWAX_LLM_PROTOCOL`, single-turn and multi-turn calls, domain error handling. Target audience: cell `applications/discover/` (uses the LLM to build the traceability graph).

The `llm/` cell encapsulates only transport — it accepts ready-made prompts and returns the raw response text. Domain logic (prompt assembly, JSON parsing, multi-turn orchestration) lives in the consumer. Providers (Anthropic, OpenAI) are switched via an environment variable without changing the consumer's code.

---

## Obtaining the client

`build_llm_client` selects an adapter based on `SWAX_LLM_PROTOCOL` and pins the model
from `SWAX_LLM_MODEL`:

```python
from swax.llm import build_llm_client, LLMClient


def get_llm() -> LLMClient:
    return build_llm_client()
```

Consumer conventions:
- Before calling, ensure that `require_vars` (cell `config/`) has already run — otherwise `MissingEnvironmentVariablesError` will be raised from inside `build_*_client` (it checks all four `SWAX_LLM_*` variables, including `SWAX_LLM_MODEL`).
- On an unknown protocol it raises `UnsupportedLLMProtocolError` — the CLI handler maps it to `click.ClickException`.
- Returns an object satisfying the `LLMClient` protocol — the concrete adapter type is hidden.
- The model name is set by the user via `SWAX_LLM_MODEL`; the consumer does not need to know or pass the model — it is baked into the adapter at construction time.

---

## Single-turn call

`ask` sends one system + one user message and returns the raw response text:

```python
from swax.prompts import build_graph_system_prompt, build_graph_user_prompt
from swax.llm import build_llm_client


def first_pass(endpoints: list[str]) -> str:
    client = build_llm_client()
    system = build_graph_system_prompt()
    user = build_graph_user_prompt(endpoints)
    return client.ask(system=system, user=user)
```

Consumer conventions:
- Returns the response text (a string). JSON parsing is the consumer's responsibility.
- On an API error it raises `LLMCallError` or `LLMRateLimitedError`.

---

## Multi-turn call

`ask_multi_turn` sends a system message + an ordered message history — for the refinement pass:

```python
from swax.llm import build_llm_client


def refine_pass(system: str, first_user: str, first_response: str, refine_user: str) -> str:
    client = build_llm_client()
    return client.ask_multi_turn(
        system=system,
        messages=[
            {"role": "user", "content": first_user},
            {"role": "assistant", "content": first_response},
            {"role": "user", "content": refine_user},
        ],
    )
```

Consumer conventions:
- `messages` — an ordered list of user/assistant roles. Order is critical — the SDK builds the context from it.
- `system` is passed separately (not included in `messages`) — Anthropic and OpenAI have different conventions, and the `llm/` cell encapsulates this.

---

## Domain exception handling

All API errors are wrapped in domain exceptions. There is no retry policy — that is the consumer's responsibility:

```python
from swax.llm import LLMCallError, LLMRateLimitedError


def safe_llm_call(client, system, user):
    try:
        return client.ask(system=system, user=user)
    except LLMRateLimitedError:
        # optional: retry with backoff
        raise
    except LLMCallError as exc:
        # click.ClickException(f"LLM failure: {exc.reason}")
        raise
```

`LLMRateLimitedError` and `LLMCallError` carry `reason` — the original SDK message.

---

## Testing

In tests, mock the SDK client at its import point (conventions — Mocks). Do not call the live API:

```python
def test_first_pass(mocker):
    mock_client = mocker.MagicMock()
    mock_client.ask.return_value = '{"endpoints": []}'
    # ... pass mock_client directly into the use case ...
```

The adapters accept the SDK client via constructor injection — this allows testing them with mock objects without patching.
