# Discover traceability — use case for full graph rebuild

## Domain

Invocation template for the API traceability graph full-rebuild use case. Target audience: cell `commands/discover/` (the CLI handler delegates to `run_discover` after loading `.env`).

The use case orchestrates five domain cells in a two-pass LLM scenario: `config/` (read configuration), `openapi/` (parse specifications), `prompts/` (build prompts), `llm/` (API calls), `traceability/` (persist the graph). The cell locally performs defensive JSON parsing and multi-turn message assembly.

---

## Running the use case

`run_discover` accepts only `project_root` — all other inputs are read from `.swax/config.yml`:

```python
from pathlib import Path

from swax.applications.discover import run_discover


def rebuild_graph(project_root: Path) -> None:
    run_discover(project_root=project_root)
```

Consumer conventions:
- The command requires LLM creds — `require_vars` is executed inside the use case, and `MissingEnvironmentVariablesError` propagates up to the CLI handler.
- The project must be initialized (`init`) — `.swax/config.yml` must exist.
- Always builds a fresh graph, ignoring any existing `.swax/traceability.yml`.

---

## What runs inside (two-pass scenario)

The use case performs 15 steps:

**Preparation (steps 1-5):**
1. `require_vars` — fail fast when LLM creds are missing.
2. `load_config` — read `.swax/config.yml`.
3. Resolve the specs root from `config.specs.location`.
4. `discover_specs` — list specification files.
5. For each specification: `parse_spec` -> `extract_paths` (accumulate endpoints) + `extract_schemas` (accumulate schema context).

**First LLM pass (steps 6-9):**
6. `build_llm_client` — factory selected by `SWAX_LLM_PROTOCOL`.
7. `build_graph_system_prompt` + `build_graph_user_prompt(endpoints)`.
8. `client.ask(system, first_user)` -> defensive JSON parsing -> dependency hypotheses.
9. Extract ambiguous pairs (pairs the LLM marked as uncertain).

**Refinement LLM pass (steps 10-11):**
10. `build_refine_user_prompt(ambiguous_pairs, schemas)`.
11. `client.ask_multi_turn(system, [initial_user, assistant_response, refine_user])` -> defensive JSON parsing -> final dependencies.

**Graph assembly and persistence (steps 12-16):**
12. Merge confident edges from the first pass with resolved uncertain pairs from the refinement pass. The refinement overrides the first pass only when its adjacency list is non-empty; an empty refinement response is treated as "no new information", and the confident edges are preserved.
13. Every endpoint extracted from the specifications is guaranteed to be present in the final map (with an empty list if it has no edges).
14. Sources and targets outside the set of endpoints are filtered out — this honors the prompt contract that forbids paths outside the endpoint universe.
15. `TraceabilityGraph(edges={})` + `add_edge` for each dependency pair; endpoints without edges are added as keys with empty lists.
16. `graph.deduplicate()` — removes duplicates and self-loops (empty keys are retained as graph nodes), `save_traceability(graph, .swax/traceability.yml)`, INFO log on completion.

---

## Domain exception handling

`run_discover` does NOT catch exceptions — they propagate upward. The CLI handler maps them:

```python
from swax.applications.discover import run_discover
from swax.config import MissingEnvironmentVariablesError
from swax.llm import LLMCallError, LLMRateLimitedError, LLMResponseParseError
from swax.openapi import SpecParseError


def safe_discover(project_root):
    try:
        run_discover(project_root=project_root)
    except MissingEnvironmentVariablesError as exc:
        # click.ClickException(f"Missing variables: {', '.join(exc.missing)}")
        ...
    except SpecParseError as exc:
        # click.ClickException(f"Parse error in {exc.path}: {exc.reason}")
        ...
    except LLMRateLimitedError:
        # click.ClickException("LLM rate limit exceeded")
        ...
    except LLMCallError as exc:
        # click.ClickException(f"LLM failure: {exc.reason}")
        ...
    except LLMResponseParseError as exc:
        # click.ClickException(f"LLM response parse error: {exc.reason}")
        ...
```

The application layer knows nothing about CLI/Click — this is the separation of concerns.

---

## Testing

`run_discover` is tested by mocking domain routines at their import point. Use `tmp_path` for `project_root` and a pre-written `.swax/config.yml`:

```python
def test_run_discover_builds_graph(tmp_path, mocker):
    # prepare .swax/config.yml in tmp_path
    # mock discover_specs, parse_spec, extract_paths to return fixtures
    # mock build_llm_client and LLMClient.ask/ask_multi_turn to return JSON responses
    run_discover(project_root=tmp_path)
    assert (tmp_path / ".swax" / "traceability.yml").exists()
```

Never call the live LLM API in tests — always mock.
