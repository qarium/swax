# Plan impact report — use case for change-impact analysis

## Domain

Invocation template for the API change-impact analysis use case. Target audience: cell
`commands/plan/` (the CLI handler delegates to `run_plan` after loading `.env`).

The use case orchestrates six domain cells in a single-pass LLM scenario: `config/` (read config),
`git/` (clone fresh specs), `openapi/` (parse + diff + classify), `traceability/` (load graph +
map affected), `prompts/` (build prompts), `llm/` (one `ask` call). Defensive JSON parsing and
risk validation happen locally.

## Running the use case

`run_plan` accepts only `project_root`; all other inputs come from `.swax/config.yml`:

```python
from pathlib import Path
from swax.applications.plan import run_plan

markdown = run_plan(project_root=Path.cwd())
print(markdown)
```

Consumer conventions:
- Requires LLM creds — `require_vars` runs inside; `MissingEnvironmentVariablesError` propagates.
- The project must be initialized and discovered — `.swax/config.yml` and `.swax/traceability.yml` must exist.
- Returns the Markdown string; the caller (handler) is responsible for echoing it to stdout.

## What runs inside

1. `require_vars` — fail fast on missing LLM creds.
2. `load_config` — repo URL, specs location, local baseline root.
3. `load_traceability` — missing file raises `TraceabilityGraphMissingError` (run `discover`).
4. `clone_specs` (ctx-mgr) → `discover_specs` + `parse_spec` over fresh specs.
5. `discover_specs` + `parse_spec` over the local baseline.
6. Per matching file pair: `diff_specs` → `classify_endpoint_changes`; merge into one `EndpointDiff`.
7. No changes → build `ImpactReport(summary="No changes detected", risk="LOW")`, skip LLM.
8. Else `find_affected_endpoints(changed_paths, graph)`, build prompts, one `LLMClient.ask`.
9. Defensive JSON parse → `ImpactReport`; validate risk (fallback MEDIUM).
10. `render_impact_report` → return Markdown.

## Domain exception handling

`run_plan` does NOT catch exceptions — they propagate. The CLI handler maps them.

## Testing

Mock domain routines at their import point; use `tmp_path` for `project_root` with a pre-written
`.swax/config.yml` and `.swax/traceability.yml`. Never call the live LLM API — always mock.
