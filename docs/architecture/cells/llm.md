---
title: swax/llm
description: Provider-agnostic LLM transport — LLMClient protocol, Anthropic and OpenAI adapters, factory by SWAX_LLM_PROTOCOL.
---

# `swax/llm`

Provider-agnostic LLM transport. Adapters wrap the Anthropic and OpenAI SDKs
behind a single protocol; the factory selects one by `SWAX_LLM_PROTOCOL`.

Adapters receive the SDK client and the model identifier via **constructor
injection** — for testability via mock at import point. The model is read from
`SWAX_LLM_MODEL` by `build_llm_client` and forwarded to the chosen adapter.
`SWAX_LLM_TOKEN` never appears in logs. Relative imports inside the cell.

`require_vars` is the entry point for credential validation;
`MissingEnvironmentVariablesError` propagates to the caller.

## Protocol

### `LLMClient()`

Structural protocol for LLM transports. Adapters satisfy it implicitly — no
inheritance required.

The protocol is **domain-agnostic**: methods accept pre-built system/user
strings and return raw response text. Multi-step orchestration (dependency
inference, schema refinement) lives in the consumer, not here.

| Method | Signature | Description |
| --- | --- | --- |
| `ask` | `(system: str, user: str) -> response: str` | Single-turn transport: sends one system + one user message, returns raw response text. SDK errors are mapped to `LLMCallError` / `LLMRateLimitedError`. |
| `ask_multi_turn` | `(system: str, messages: list[dict[str, str]]) -> response: str` | Multi-turn transport: sends a system prompt plus an ordered message history, returns raw response text. Message order is preserved — the SDK relies on it for context continuity. SDK errors are mapped to `LLMCallError` / `LLMRateLimitedError`. |

## Adapters

### `LLMClient::AnthropicAdapter(client: Anthropic, model: str)`

`LLMClient` backed by the Anthropic SDK.

- `client`: injected Anthropic SDK client, constructed by
  `build_anthropic_client`.
- `model`: model identifier sent on every request, supplied by
  `build_llm_client` from `SWAX_LLM_MODEL`.

Requirements:

- Method signatures match the `LLMClient` protocol **exactly** — provider
  switching requires no consumer code change.

Properties:

| Property | Type | Description |
| --- | --- | --- |
| `client` | `Anthropic` | The injected Anthropic SDK client instance. |
| `model` | `str` | The injected model identifier sent on every request. |

Methods:

- `ask(system, user) -> response: str` — sends a single user message with the
  system prompt at the injected model; concatenates text content blocks of the
  response; maps rate-limit errors to `LLMRateLimitedError` and other API
  errors to `LLMCallError`.
- `ask_multi_turn(system, messages) -> response: str` — sends the message
  history with the system prompt; concatenates text content blocks; maps
  errors as in `ask`.

### `LLMClient::OpenAIAdapter(client: OpenAI, model: str)`

`LLMClient` backed by the OpenAI SDK.

- `client`: injected OpenAI SDK client, constructed by `build_openai_client`.
- `model`: model identifier sent on every request, supplied by
  `build_llm_client` from `SWAX_LLM_MODEL`.

Requirements:

- Method signatures match the `LLMClient` protocol **exactly** — provider
  switching requires no consumer code change.

Properties:

| Property | Type | Description |
| --- | --- | --- |
| `client` | `OpenAI` | The injected OpenAI SDK client instance. |
| `model` | `str` | The injected model identifier sent on every request. |

Methods:

- `ask(system, user) -> response: str` — submits a system message followed by
  the user message at the injected model; returns the first choice's message
  content (empty string when absent); maps rate-limit errors to
  `LLMRateLimitedError` and other API errors to `LLMCallError`.
- `ask_multi_turn(system, messages) -> response: str` — prepends the system
  prompt to the message list, submits the combined messages at the injected
  model; returns the first choice's message content; maps errors as in `ask`.

## Factory

### `build_llm_client() -> client: LLMClient`

Factory selecting the adapter based on `SWAX_LLM_PROTOCOL`.

- `client`: an `LLMClient`-shaped adapter wrapping the chosen SDK client and
  pinned to the model named by `SWAX_LLM_MODEL`.

Algorithm:

1. Read `SWAX_LLM_PROTOCOL` from the environment.
2. Construct the matching SDK client via `build_anthropic_client` /
   `build_openai_client` (which call `require_vars` first, so a missing
   `SWAX_LLM_MODEL` surfaces as `MissingEnvironmentVariablesError` before it
   is read here).
3. Read `SWAX_LLM_MODEL` from the environment and forward it to the adapter.
4. On an unknown protocol value, raise `UnsupportedLLMProtocolError`.

Requirements:

- Switching providers requires **no code change** in consumers.
- Selecting a model requires **no code change** in consumers.
- Protocol value is validated upstream.

### `build_anthropic_client() -> client: Anthropic`

Constructs an Anthropic SDK client from `SWAX_LLM_*` environment variables.

Algorithm:

1. Call `require_vars` to fail fast on missing credentials.
2. Read the LLM token and base URL from the environment.
3. Construct and return the SDK client.

Requirements:

- Credentials are read from the environment, **never hardcoded**.
- Base URL is assumed already validated (no `/v1`).

### `build_openai_client() -> client: OpenAI`

Constructs an OpenAI SDK client from `SWAX_LLM_*` environment variables.

Algorithm:

1. Call `require_vars` to fail fast on missing credentials.
2. Read the LLM token and base URL from the environment.
3. Construct and return the SDK client.

Requirements:

- Credentials are read from the environment, **never hardcoded**.
- Base URL is assumed already validated (no `/v1`) — the SDK adds the version
  segment itself.

## Errors

| Exception | Cause |
| --- | --- |
| `LLMCallError(reason: str)` | Raised by adapters on a generic LLM API error (non-rate-limit). |
| `LLMRateLimitedError(reason: str)` | Raised by adapters when the LLM API returns a rate-limit error. |
| `LLMResponseParseError(reason: str, excerpt: str)` | Raised by **LLM consumers** when defensive JSON parsing of an LLM response fails. `excerpt` is the raw payload excerpt (first 200 chars) for diagnostics; never contains credentials. |
| `UnsupportedLLMProtocolError(protocol: str)` | Raised by `build_llm_client` when `SWAX_LLM_PROTOCOL` is neither `anthropic` nor `openai`. |

## See also

- [Configuration](../../getting-started/configuration.md) — `SWAX_LLM_*`
  variables.
- [Architecture / prompts cell](prompts.md) — produces the strings passed to
  `ask` / `ask_multi_turn`.
