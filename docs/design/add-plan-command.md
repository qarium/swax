# Design Document: `add-plan-command`

The `plan` command analyzes differences between the local (baseline) API
specifications and the fresh specification state cloned from the repository,
maps the changes onto the traceability graph, and emits a Markdown Impact Report
about the testing impact of those changes (to stdout).

This document is a **complete architectural specification** derived from the
materialized `CODEMANIFEST` changes (8 cells). It specifies **what** to
implement and **how** — every entry point is traced, every algorithm elaborated,
every cross-cutting concern fixed, and every test scenario recorded. It does not
write implementation code; that is the job of the `goga-plan` / `goga-build`
stage that consumes this document.

The design reuses the layered architecture from `docs/design/1-init-and-discover.md`
(`cli → commands → applications → domain cells`) and the established single-turn
LLM + defensive-JSON-parse pattern of `run_discover`.

---

## Contract Changes

Source of truth for the contract: the materialized `CODEMANIFEST` files on the
`add-plan-command` branch. `goga lint` → **16 cells, 0 errors**; `goga schema`
confirms the dependency map with no cycles.

### Changed CODEMANIFEST Files

- **`swax/openapi/CODEMANIFEST`** (modified) — added the `deepdiff` usage, a new
  global-annotation paragraph about structural diffing/classification, and three
  new type declarations (`diff_specs`, `classify_endpoint_changes`,
  `EndpointDiff`). Existing types unchanged. Footer description extended.
- **`swax/traceability/CODEMANIFEST`** (modified) — added two type declarations
  (`find_affected_endpoints`, `TraceabilityGraphMissingError`). Header unchanged
  (cell stays import-free). Footer description extended.
- **`swax/prompts/CODEMANIFEST`** (modified) — extended the global annotation to
  mention the single-turn Impact Report scenario and added two routine builders
  (`build_impact_report_system_prompt`, `build_impact_report_user_prompt`). Cell
  stays import-free.
- **`swax/applications/CODEMANIFEST`** (modified facade) — added
  `run_plan AS run_plan_handler` import from `swax/applications/plan`, the
  `->run_plan_handler: {}` embedding, and the annotation paragraph listing the
  third re-export.
- **`swax/commands/CODEMANIFEST`** (modified facade) — added
  `plan AS plan_handler` import from `swax/commands/plan`, the
  `->plan_handler: {}` embedding, and the annotation paragraph.
- **`swax/cli/CODEMANIFEST`** (modified) — no new imports/types (registration
  stays lazy in `__main__.py` to keep the contract acyclic). Global annotation
  and the `main` annotation extended to mention `plan` lazy registration.

### New Entities

- **`diff_specs(base: dict, current: dict) -> diff: DeepDiff`** — `swax/openapi`,
  `diff_specs.py`. Structural diff of two dereferenced specs (Routine).
- **`classify_endpoint_changes(diff: DeepDiff) -> changes: EndpointDiff`** —
  `swax/openapi`, `classify_endpoint_changes.py`. Classifies a raw diff into
  endpoint-level added/removed/modified changes (Routine).
- **`EndpointDiff(added: list[str], removed: list[str], modified: dict[str, list[str]])`**
  — `swax/openapi`, `endpoint_diff.py`. Classified change result (Entity with
  `added`/`removed`/`modified` properties and `has_changes()` /
  `changed_paths()` methods).
- **`find_affected_endpoints(changed_paths: list[str], graph: TraceabilityGraph) -> affected: list[str]`**
  — `swax/traceability`, `find_affected_endpoints.py`. Reverse-reachability
  traversal over the graph (Routine).
- **`TraceabilityGraphMissingError(path: pathlib.Path)`** — `swax/traceability`,
  `errors.py`. Domain error raised when `.swax/traceability.yml` is absent.
- **`build_impact_report_system_prompt() -> prompt: str`** — `swax/prompts`,
  `build_impact_report_system_prompt.py`. Constant system prompt for the impact
  analyst role (Routine).
- **`build_impact_report_user_prompt(added, removed, modified, affected, graph_context) -> prompt: str`**
  — `swax/prompts`, `build_impact_report_user_prompt.py`. User prompt carrying
  structured change context (Routine).
- **`run_plan(project_root: pathlib.Path) -> markdown: str`** —
  `swax/applications/plan`, `run_plan.py`. The plan use-case orchestrator
  (Routine).
- **`ImpactReport(summary, risk, modified, affected, requirements, checklist)`** —
  `swax/applications/plan`, `impact_report.py`. Structured LLM output model
  (Entity with 6 properties).
- **`render_impact_report(report: ImpactReport) -> markdown: str`** —
  `swax/applications/plan`, `render_impact_report.py`. Pure transformation to the
  Markdown report template (Routine).
- **`plan(ctx: click.Context)`** — `swax/commands/plan`, `plan.py`. Thin Click
  handler: delegate, echo, map 9 domain exceptions (Entity, single method).

### Changed Entities

- **`swax/cli.__main__`** (registration site, not a CODEMANIFEST type) — already
  modified by the prior `apply-architecture` stage per the user's choice A:
  imports `plan_handler` from the `swax/commands` facade and registers it as
  `main.add_command(plan_handler, name="plan")`, mirroring `init`/`discover`.

### Deleted Entities

None.

### Usages and Annotations Changes

- **`swax/openapi`** — `Usages` gained `deepdiff: .goga/usages/cooks/deepdiff.md`;
  global annotation gained the diffing/classification paragraph and the
  `Use \`deepdiff\`` hint.
- **`swax/applications/plan`** — new `Usages` entry `json` (inline) for
  defensive JSON parsing; global annotation fixes the defensive-parse, risk
  fallback, and exception-propagation rules.
- **`swax/commands/plan`** — `Usages` entries `conventions` + `click`; global
  annotation fixes the exception-mapping discipline.
- Facade annotations (`swax/applications`, `swax/commands`) extended to list the
  third handler re-export.

---

## Applied Fixes

### Static contract validation result

The materialized CODEMANIFEST is **clean** — `goga lint` reports 0 errors and
`goga schema` reports no cycles. No blocking `CODEMANIFEST` defects were found
during the four-dimension consistency audit, so no user-approval / edit cycle
(Phase 3 Step 4) was required. The findings below are clarifications recorded
**into this design document** (not CODEMANIFEST edits) so the implementation
agent resolves them deterministically.

### Recorded clarifications (design-level, no CODEMANIFEST edit)

- **`load_traceability` does not raise on a missing file.** Its contract returns
  an empty graph when the file is absent (`storage.py` reads `""` for a missing
  path). `run_plan` therefore owns the missing-graph check: it tests
  `traceability_path.exists()` **before** calling `load_traceability` and raises
  `TraceabilityGraphMissingError(path)` itself. This mirrors the established
  pattern where a domain error defined in one cell is raised by an application
  consumer (cf. `LLMResponseParseError` defined in `llm`, raised by
  `run_discover`).
- **Propagation of `SpecParseError` / `UnsupportedLLMProtocolError` is implicit.**
  The `run_plan` annotation enumerates the propagated errors central to the
  use-case's own logic (`RepositoryCloneError`, `SpecsNotFoundError`,
  `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError`,
  `TraceabilityGraphMissingError`). `SpecParseError` (from `parse_spec` in steps
  4–5) and `UnsupportedLLMProtocolError` (from `build_llm_client` in step 9) also
  propagate uncaught and are mapped by the CLI handler. This is identical to the
  `run_discover` precedent (whose annotation likewise omits them while the
  `discover` handler maps them). Not a defect — consistent documentation style.
- **`graph_context` terminology.** The `build_impact_report_user_prompt` param
  `graph_context` is described in the usage as "path -> dependents". The graph
  stores `source -> [targets-it-depends-on]` (i.e. **dependencies**, not
  dependents). The implementation derives `graph_context` as the relevant
  **slice of `graph.edges`** for the affected paths: `{p: graph.edges.get(p, [])
  for p in affected}` — i.e. for each affected endpoint, the endpoints it depends
  on. This gives the LLM the dependency context it needs to reason about impact.
  The "dependents" wording in the usage is loose; the slice above is the
  authoritative derivation.
- **Context-trimming threshold.** The `run_plan` annotation says "trim to the
  most relevant entries … changed paths first, then nearest dependents" when the
  affected set is large. This design fixes a concrete, deterministic strategy
  (see `run_plan` algorithm, step 8): a single cap `_MAX_AFFECTED = 100`; keep
  changed paths first, then the sorted remainder, truncated to the cap;
  both `graph_context` and the `affected` list passed to the prompt are restricted
  to the kept set (changed first, then sorted remainder). A `WARNING` log records the
  truncation. The cap is a tuning constant, not part of the contract.

### Review corrections (design-review stage)

The four-dimension audit in `code-design` checked the contract for internal
consistency but did not exercise the external `deepdiff` API. The `design-review`
stage installed `deepdiff==9.1.0` and traced the classification path empirically,
surfacing one Critical defect that is corrected here and in the contract:

- **`deepdiff` has no `keys_added` / `keys_removed` categories.** Verified with
  `DeepDiff(...).get("keys_added", []) → []` and `hasattr(diff, "keys_added") is False`.
  The real categories are `dictionary_item_added` / `dictionary_item_removed`
  (ordered sets of path strings) and `values_changed` / `type_changes` (dicts keyed
  by path). The earlier algorithm/trace/test referenced the non-existent names, so
  `classify_endpoint_changes` would have returned empty `added`/`removed` for every
  diff → `has_changes() == False` for add/remove-only changes → a silent "No changes
  detected" report and a failing `test_diff_specs_detects_added_endpoint`. Corrected
  in `swax/openapi/CODEMANIFEST` (`classify_endpoint_changes` annotation),
  `.goga/usages/cooks/deepdiff.md`, and the Algorithm / Code Stack Trace / Test
  sections below. `classify_endpoint_changes` now also sorts `added`/`removed`/
  `modified` for determinism (the categories are ordered sets; iteration order is
  not stable across processes).

---

## Entity Interaction and Data Flow

### Interaction Diagram

```
                       swax plan  (Click)
                            │
                            ▼
                 swax/commands/plan/plan.py   ── maps 9 domain errors → ClickException
                            │  run_plan(project_root=Path.cwd())
                            ▼
              swax/applications/plan/run_plan.py   (use-case orchestrator)
                            │
   ┌────────────────────────┼─────────────────────────────────────────────┐
   │ 1. require_vars ◀──── swax/config        (LLM creds)
   │ 2. load_config  ◀──── swax/config        (Config: git.url, git.location, specs.location)
   │ 3. traceability.yml exists? ── no ──▶ raise TraceabilityGraphMissingError ◀─ swax/traceability
   │      yes ▼
   │    load_traceability ◀──── swax/traceability        (TraceabilityGraph)
   │ 4. clone_specs (ctx-mgr) ◀──── swax/git            (fresh specs dir; raises RepositoryCloneError / SpecsNotFoundError)
   │      └─ discover_specs + parse_spec ◀──── swax/openapi   (fresh spec dicts)
   │ 5. discover_specs + parse_spec ◀──── swax/openapi        (baseline spec dicts)
   │ 6. per matching pair: diff_specs → classify_endpoint_changes ◀──── swax/openapi (EndpointDiff)
   │      merge all pairs → one EndpointDiff
   │ 7. has_changes()?  ── no ──▶ ImpactReport("No changes detected", "LOW") ──▶ render ──▶ return
   │      yes ▼
   │ 8. find_affected_endpoints(changed_paths, graph) ◀──── swax/traceability   (affected: list[str])
   │      build graph_context slice
   │      build_impact_report_system_prompt + build_impact_report_user_prompt ◀──── swax/prompts
   │ 9. build_llm_client ◀──── swax/llm   (LLMClient; raises UnsupportedLLMProtocolError)
   │      client.ask(system, user)        (raises LLMCallError / LLMRateLimitedError)
   │      defensive JSON parse → ImpactReport   (json.JSONDecodeError → LLMResponseParseError; risk fallback MEDIUM)
   │ 10. render_impact_report(report) → markdown: str
   └────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
            plan.py echoes markdown to stdout  (click.echo)
```

### Data Flows

#### Flow: `swax plan` (the only flow — single-turn)

Participating entities and the data passed between them, in execution order:

1. `plan(ctx)` → resolves `project_root = pathlib.Path.cwd()`; calls
   `run_plan(project_root)`.
2. `run_plan` → `require_vars()` → validates `SWAX_LLM_*` env vars (raises
   `MissingEnvironmentVariablesError`).
3. `run_plan` → `load_config(project_root/".swax"/"config.yml")` → `Config`
   (`git.url`, `git.location`, `specs.location`).
4. `run_plan` → existence check on `project_root/".swax"/"traceability.yml"`:
   absent → `TraceabilityGraphMissingError`; present →
   `load_traceability(path)` → `TraceabilityGraph`.
5. `run_plan` → `with clone_specs(config.git.url, config.git.location) as fresh_root:`
   → fresh specs directory (raises `RepositoryCloneError` /
   `SpecsNotFoundError`); inside, `discover_specs(fresh_root)` → fresh spec
   paths, each `parse_spec(p)` → fresh spec dict, keyed by relative path.
6. `run_plan` → `discover_specs(project_root/config.specs.location)` → baseline
   paths, each `parse_spec(p)` → baseline spec dict, keyed by relative path.
7. For each matching relative path: `diff_specs(base, current)` → `DeepDiff` →
   `classify_endpoint_changes(diff)` → per-pair `EndpointDiff`; all merged into
   one aggregate `EndpointDiff`.
8. `EndpointDiff.has_changes()` → `False`: build no-change `ImpactReport`,
   skip to step 10.
9. `has_changes()` → `True`:
   `find_affected_endpoints(merged.changed_paths(), graph)` → `affected: list[str]`;
   `_build_graph_context(affected, changed, graph)` → `(graph_context, trimmed_affected)`
   (both trimmed to the kept set: changed first, then sorted remainder);
   `build_impact_report_system_prompt()` → system str;
   `build_impact_report_user_prompt(added, removed, modified, trimmed_affected, graph_context)`
   → user str.
10. `build_llm_client()` → `LLMClient`; `client.ask(system, user)` → raw str;
    defensive parse → `ImpactReport` (risk constrained to `HIGH`/`MEDIUM`/`LOW`).
11. `render_impact_report(report)` → `markdown: str`; returned to `plan`.
12. `plan` → `click.echo(markdown)`.

### Entity Dependencies

Initialization / dependency order (matches the architecture plan, leaves first):

- **Domain leaves (import-free)** — `swax/config`, `swax/git`, `swax/llm`,
  `swax/openapi` (now with the diff subsystem), `swax/traceability` (now with
  traversal + missing-graph error), `swax/prompts` (now with impact-report
  builders).
- **`swax/applications/plan`** ← config, git, openapi, traceability, prompts,
  llm (six `Imports` groups).
- **`swax/applications`** (facade) ← `applications/plan` (`run_plan` as
  `run_plan_handler`).
- **`swax/commands/plan`** ← applications (run_plan, via the facade), cli
  (SwaxContext), and the domain error types from config / openapi / git /
  traceability / llm.
- **`swax/commands`** (facade) ← `commands/plan` (`plan` as `plan_handler`).
- **`swax/cli`** ← config only; `plan` is registered lazily in
  `__main__.py`, breaking the `cli ↔ commands` cycle.

---

## Code Stack Trace

Every checkpoint below is **passed** (no CODEMANIFEST defect surfaced). External
API usage is verified against the actual source files and the referenced
`.usages` / `.goga/usages` documents, not assumed.

### Trace: `swax plan` (end-to-end entry point)

#### Chain

1. **Input** — the user runs `swax plan`. Click dispatches to `plan` because
   `__main__.py` registered `plan_handler` under `name="plan"`. `ctx.obj` is the
   `SwaxContext` built by the `main` group callback (env already loaded by
   `load_env`). → checkpoint: `ctx.obj` is a `SwaxContext`? **passed** — `main`
   constructs it; `@click.pass_obj` forwards it.
2. **Step** — `plan` resolves `project_root = pathlib.Path.cwd()`. No options,
   no prompts. → checkpoint: matches the contract "reads everything from
   `.swax/config.yml` and the environment"? **passed**.
3. **Step** — `plan` calls `run_plan(project_root)` inside a `try`. → checkpoint:
   `run_plan` signature `(project_root: pathlib.Path) -> markdown: str` matches
   the call? **passed** — single positional arg.
4. **Step (inside `run_plan`)** — `require_vars()` runs first. Raises
   `MissingEnvironmentVariablesError(missing=[...])` if any `SWAX_LLM_*` is
   missing. → checkpoint: error carries `.missing: list[str]` for the handler
   message? **passed** (`config/errors.py`).
5. **Step** — `load_config(path)` → `Config`. → checkpoint: `Config.git.url`,
   `Config.git.location`, `Config.specs.location` exist and are `str`?
   **passed** (`GitConfig`, `SpecsConfig`).
6. **Step** — `traceability_path.exists()`? **No** → raise
   `TraceabilityGraphMissingError(path)`. **Yes** → `load_traceability(path)` →
   `TraceabilityGraph`. → checkpoint: `TraceabilityGraphMissingError(path)`
   constructor matches `swax/traceability/errors.py`? **passed** (keyword
   `path=`). And `load_traceability` returns `TraceabilityGraph`, not `None`?
   **passed**.
7. **Step** — `with clone_specs(config.git.url, config.git.location) as fresh_root:`
   yields the fresh specs dir. → checkpoint: `clone_specs(repo_url: str,
   specs_location: str)` signature matches `(config.git.url, config.git.location)`?
   **passed** (`git/clone_specs.py`). Raises `RepositoryCloneError(url=, reason=)`
   / `SpecsNotFoundError(path=)`? **passed** — attribute names match
   `git/errors.py`.
8. **Step** — `discover_specs(fresh_root)` → sorted `list[Path]`; each
   `parse_spec(p)` → `dict`. Same for baseline root
   `project_root/config.specs.location`. → checkpoint: `discover_specs(root)` and
   `parse_spec(spec_path)` signatures match? **passed**. `parse_spec` can raise
   `SpecParseError(path, reason)` — propagates (handler maps it).
9. **Step** — match baseline and fresh specs by relative path; for each pair:
   `diff_specs(base, current)` → `DeepDiff`; `classify_endpoint_changes(diff)` →
   `EndpointDiff`; merge. → checkpoint: `diff_specs(base: dict, current: dict) ->
   diff: DeepDiff` and `classify_endpoint_changes(diff: DeepDiff) -> changes:
   EndpointDiff` signatures match? **passed**. `EndpointDiff` exposes
   `added`/`removed`/`modified`/`has_changes()`/`changed_paths()`? **passed** —
   declared in the same CODEMANIFEST.
10. **Step** — `has_changes()`? **False** → `ImpactReport(summary="No changes
    detected", risk="LOW", modified=[], affected=[], requirements=[],
    checklist=[])`. → checkpoint: `ImpactReport` constructor accepts those 6
    keyword fields? **passed** — declared properties match exactly.
11. **Step** — `has_changes()` **True** →
    `find_affected_endpoints(merged.changed_paths(), graph)` → `affected`.
    → checkpoint: `find_affected_endpoints(changed_paths: list[str], graph:
    TraceabilityGraph) -> affected: list[str]` matches
    `(merged.changed_paths() which is list[str], graph)`? **passed**. Then
    `build_impact_report_system_prompt() -> str` and
    `build_impact_report_user_prompt(added, removed, modified, affected,
    graph_context) -> str`. → checkpoint: the five user-prompt args are
    `list[str], list[str], dict[str, list[str]], list[str], dict[str, list[str]]`?
    `merged.added`/`removed` are `list[str]`; `merged.modified` is
    `dict[str, list[str]]`; `affected` is `list[str]`; `graph_context` is
    `dict[str, list[str]]`. **passed** — types align.
12. **Step** — `client = build_llm_client()` → `LLMClient`; `raw =
    client.ask(system=..., user=...)`. → checkpoint: `ask(self, system: str,
    user: str) -> str`? **passed** (`llm/llm_client.py`). `build_llm_client() ->
    LLMClient`? **passed**. Can raise `UnsupportedLLMProtocolError(protocol=)`
    (propagates) and `LLMCallError` / `LLMRateLimitedError` (propagate). →
    **passed**.
13. **Step** — defensive parse of `raw` into `ImpactReport`; risk fallback to
    `MEDIUM`. → checkpoint: on parse failure, raise
    `LLMResponseParseError(reason=, excerpt=)`? **passed** — constructor matches
    `llm/errors.py`.
14. **Output** — `render_impact_report(report) -> markdown: str` returned to
    `plan`, which `click.echo`s it. → checkpoint: `render_impact_report(report:
    ImpactReport) -> markdown: str` matches? **passed**.

#### Checkpoint Summary

- All type flows between cells align (list[str] / dict[str, list[str]] /
  DeepDiff / TraceabilityGraph / EndpointDiff / ImpactReport / Config / Path /
  str). **passed**.
- All imported types exist in their source cells and expose the attributes the
  consumer references (`Config.git.url|location`, `Config.specs.location`,
  `EndpointDiff.has_changes()|changed_paths()`, `LLMClient.ask`,
  `TraceabilityGraph.edges`, the error `.missing`/`.path`/`.reason`/`.url`/
  `.protocol`/`.excerpt` attributes). **passed**.
- No `Type::` mutations and no `->` embeddings in `applications/plan` (it is a
  plain orchestrator). The facades use embeddings (`->run_plan_handler: {}`,
  `->plan_handler: {}`) backed by valid `Imports`. **passed**.

### Trace: `diff_specs(base, current)`

1. **Input** — two fully dereferenced spec dicts (output of `parse_spec`).
2. **Step** — `DeepDiff(base, current, ignore_order=True, report_repetition=False,
   cutoff_intersection_for_pairs=1, verbose_level=1)` (per `.goga/usages/cooks/
   deepdiff.md`). → checkpoint: `deepdiff.DeepDiff` accepts those kwargs?
   **passed** (verified against the usage file).
3. **Output** — the `DeepDiff` object, returned unchanged. Classification is the
   next routine's job. **passed**.

### Trace: `classify_endpoint_changes(diff)`

1. **Input** — a `DeepDiff` from `diff_specs`.
2. **Step** — read change sets via `diff.get("dictionary_item_added", [])`,
   `diff.get("dictionary_item_removed", [])`, `diff.get("values_changed", {})` (and
   `type_changes`, `set_item_added/removed` for completeness). Each entry's path
   string has the deepdiff form `root['paths']['/users']['get']...`. → checkpoint:
   deepdiff exposes `dictionary_item_added`/`dictionary_item_removed`/`values_changed`? **passed**
   (deepdiff usage doc).
3. **Step** — for each path string, parse the `root['paths']['<endpoint>']`
   prefix. If present → classify by change set: `dictionary_item_added` under `paths` → the
   endpoint was **added**; `dictionary_item_removed` under `paths` → **removed**;
   `values_changed`/`type_changes` under `paths` → **modified** (endpoint +
   human-readable description of the changed tail). Paths under
   `components`/`definitions` are skipped — because `$ref` is already
   dereferenced, every endpoint that referenced a changed schema surfaces the
   change under its own `paths[...]` entry, so the components-level change is
   redundant. → checkpoint: does this satisfy "attribute schema changes to the
   endpoints that use them"? **passed** — dereferencing performs the attribution
   automatically; the classifier only needs to walk `paths`.
4. **Step** — aggregate multiple changes on the same endpoint into a single
   `modified[endpoint] = [descriptions...]`.
5. **Output** — `EndpointDiff(added=..., removed=..., modified=...)`. →
   checkpoint: does not emit endpoints outside the union of base/current path
   keys? **passed** — only paths seen in the diff's `paths[...]` prefixes are
   emitted. **passed**.

### Trace: `EndpointDiff` (construction + methods)

1. **Input** — `added`, `removed` (`list[str]`), `modified`
   (`dict[str, list[str]]`).
2. **Step** — pydantic model, `kw_only=True` (per conventions). Three fields.
3. **Method `has_changes()`** → `bool(not (added or removed or modified))` →
   returns `True` when any of the three is non-empty. **passed**.
4. **Method `changed_paths()`** → `sorted(set(added) | set(removed) |
   set(modified.keys()))` — deterministic, deduplicated union. **passed**.

### Trace: `find_affected_endpoints(changed_paths, graph)`

1. **Input** — `changed_paths: list[str]`, `graph: TraceabilityGraph`.
2. **Step** — build the reverse adjacency from `graph.edges`: for each
   `source -> [targets]`, append `source` to `reverse[target]`. (A node's
   **dependents** are the sources whose adjacency list contains it.)
3. **Step** — BFS/DFS over reverse edges starting from every changed path:
   collect the changed path itself plus every node that transitively reaches it
   (i.e. every transitive dependent).
4. **Output** — `sorted(set)` of the affected set. Changed paths that are not
   graph nodes are still returned (they were seeded into the set at the start).
   → checkpoint: read-only (no mutation of `graph.edges`)? **passed**. Does not
   import from `openapi` (accepts plain strings)? **passed** — the cell stays
   import-free. **passed**.

### Trace: `build_impact_report_system_prompt()`

1. **Input** — none.
2. **Output** — a constant `str` fixing the role ("API change impact analyst"),
   the JSON output contract (`summary`, `risk`, `modified`, `affected`,
   `requirements`, `checklist`), the allowed risk values (`HIGH`/`MEDIUM`/`LOW`),
   and the "JSON only, no prose" rule. → checkpoint: no parameters, no embedded
   data/secrets/paths? **passed**. **passed**.

### Trace: `build_impact_report_user_prompt(added, removed, modified, affected, graph_context)`

1. **Input** — five primitive args.
2. **Step** — render `added`/`removed`/`affected` as JSON arrays,
   `modified`/`graph_context` as JSON objects (via `json.dumps`), preserving the
   caller's sorted order. Instruct the model to return the Impact Report JSON
   contract from the system prompt.
3. **Output** — the user `str`. → checkpoint: no silent truncation (the caller
   trims), no embedded secrets/paths? **passed**. **passed**.

### Trace: `render_impact_report(report)`

1. **Input** — an `ImpactReport` (LLM-produced or the no-change placeholder).
2. **Step** — pure transformation into the Markdown template (Summary, Risk,
   Modified, Affected, Requirements, Checklist). Empty lists render an explicit
   "(none)" so the section is always present and unambiguous.
3. **Output** — the Markdown `str`. → checkpoint: pure (no I/O, no LLM call),
   no synthesized content? **passed**. **passed**.

---

## Algorithm Design

For each new/changed entity. `Requirements` and `Constraints` track the
CODEMANIFEST; algorithms elaborate the implementation.

### `swax/openapi/` — diff subsystem

#### `diff_specs`

**Responsibility**: compute a raw structural diff between two dereferenced specs.

**Algorithm:**
```
1. Return DeepDiff(base, current,
     ignore_order=True,          # endpoint order is not significant
     report_repetition=False,
     cutoff_intersection_for_pairs=1,  # skip identical subtrees early (perf)
     verbose_level=1)            # never verbose_level=2 in production
   → the DeepDiff object, unchanged
```

**Errors:** none raised here.

**Edge Cases:**
- Cyclic `$ref` already collapsed to a `{"$ref": ...}` marker by `parse_spec` —
  deepdiff treats it as a normal value; no special handling.
- Identical specs → an empty `DeepDiff` (all change sets empty) → downstream
  `has_changes()` is `False`.

#### `classify_endpoint_changes`

**Responsibility**: turn a raw diff into endpoint-level added/removed/modified.

**Algorithm:**
```
1. Initialize added=[], removed=[], modified={}.
2. For each path_str in diff.get("dictionary_item_added", []) or []:
     endpoint = _extract_endpoint(path_str)         # parse root['paths']['<ep>']
     if endpoint is not None and endpoint not in added: added.append(endpoint)
3. For each path_str in diff.get("dictionary_item_removed", []) or []:
     endpoint = _extract_endpoint(path_str)
     if endpoint is not None and endpoint not in removed: removed.append(endpoint)
4. For each path_str in diff.get("values_changed", {}) or {}
                ∪ diff.get("type_changes", {}) or {}:
     endpoint = _extract_endpoint(path_str)
     if endpoint is None: continue                  # not under paths → skip (covers components/definitions)
     modified.setdefault(endpoint, []).append(_describe_change(path_str))
5. Return EndpointDiff(added=sorted(added), removed=sorted(removed),
        modified={k: sorted(v) for k, v in sorted(modified.items())}).
   (Sort for determinism: deepdiff categories are ordered sets; iteration order is
   not stable across processes.)
```

Helpers (private, same file):
- `_extract_endpoint(path_str) -> str | None` — return the endpoint captured by
  the `root['paths']['<endpoint>']` prefix, or `None` for any other root
  (`components`, `definitions`, `info`, `servers`, …). DeepDiff escapes quotes in
  path keys; parse by walking the bracketed segments, not by naive `split`.
- `_describe_change(path_str) -> str` — a short human-readable description of the
  tail after the endpoint (e.g. `"GET responses.200 changed"`,
  `"parameters changed"`). Lowercases and simplifies; never leaks raw dict
  reprs.

**Errors:** none.

**Edge Cases:**
- A schema change under `components`/`definitions` is **skipped** at step 4
  (`_extract_endpoint` returns `None`); the same change already appears under
  every consuming endpoint's `paths[...]` entry because `$ref` was dereferenced,
  so it is attributed there. A schema changed by no endpoint is correctly
  dropped (no endpoint impact).
- Multiple changes on one endpoint aggregate into `modified[endpoint]` (a list).
- Both Swagger 2.0 (`definitions`) and OpenAPI 3.x (`components.schemas`) are
  handled transparently — both store paths under `paths`.

#### `EndpointDiff`

**Responsibility**: carry the classified result.

**Algorithm:**
```
has_changes():
  return bool(added or removed or modified)

changed_paths():
  return sorted(set(added) | set(removed) | set(modified.keys()))
```

**Errors:** none.

**Edge Cases:**
- `changed_paths()` is deterministic and deduplicated even when a path appears in
  more than one bucket.

### `swax/traceability/` — traversal + missing-graph error

#### `find_affected_endpoints`

**Responsibility**: compute the full transitive affected set (reverse
reachability).

**Algorithm:**
```
1. affected = set(changed_paths)                    # seeds; changed paths always returned
2. Build reverse adjacency from graph.edges:
     reverse = {}
     for source, targets in graph.edges.items():
         for t in targets: reverse.setdefault(t, []).append(source)
3. queue = list(changed_paths)
   while queue:
     node = queue.pop()
     for dependent in reverse.get(node, []):
       if dependent not in affected:
         affected.add(dependent); queue.append(dependent)
4. return sorted(affected)
```

**Errors:** none.

**Edge Cases:**
- Changed path absent from the graph → still returned (seeded in step 1); its
  `reverse` lookup yields nothing.
- Self-loops cannot occur — `deduplicate()` removed them at save time, but the
  routine is robust to them regardless (the `if dependent not in affected` guard
  prevents infinite loops).
- No internal cap — returns the complete closure (the caller trims before the
  LLM call).

#### `TraceabilityGraphMissingError`

Keyword-only `Exception` subclass storing `path: pathlib.Path` as a public
attribute (mirrors the other domain errors). Raised by `run_plan`, not by
`load_traceability`.

### `swax/prompts/` — impact-report builders

#### `build_impact_report_system_prompt`

**Responsibility**: constant system prompt.

**Algorithm:** return a string literal fixing (a) the role ("You are an API
change impact analyst."), (b) the task ("assess the testing impact of the
provided API endpoint changes"), (c) the JSON output contract with exactly the
six keys and their types, (d) `risk ∈ {HIGH, MEDIUM, LOW}`, (e) "JSON only — no
prose, no code fences." No parameters, no embedded data.

#### `build_impact_report_user_prompt`

**Responsibility**: structured user prompt.

**Algorithm:**
```
1. added_json     = json.dumps(added)
   removed_json   = json.dumps(removed)
   modified_json  = json.dumps(modified, sort_keys=True)
   affected_json  = json.dumps(affected)
   graph_json     = json.dumps(graph_context, sort_keys=True)
2. Return a template string embedding the five JSON blocks and the instruction
   to return the Impact Report JSON contract from the system prompt.
```

**Edge Cases:** the caller (`run_plan`) trims large inputs before calling; the
builder never truncates silently.

### `swax/applications/plan/` — use-case

#### `run_plan`

**Responsibility**: the 10-step orchestrator (see Interaction Diagram).

**Algorithm:**
```
1. require_vars()                                  # MissingEnvironmentVariablesError propagates
   logger.info("plan started", extra={"project_root": str(project_root)})

2. config = load_config(project_root / ".swax" / "config.yml")

3. traceability_path = project_root / ".swax" / "traceability.yml"
   if not traceability_path.exists():
     raise TraceabilityGraphMissingError(path=traceability_path)
   graph = load_traceability(traceability_path)

4. baseline_root = project_root / config.specs.location
   baseline = _parse_spec_map(discover_specs(baseline_root), baseline_root)   # {relpath: spec dict}
   with clone_specs(config.git.url, config.git.location) as fresh_root:       # RepositoryCloneError / SpecsNotFoundError propagate
       fresh = _parse_spec_map(discover_specs(fresh_root), fresh_root)
       merged = _diff_and_classify(baseline, fresh)                           # one EndpointDiff across matching pairs

   # NOTE: parse_spec inside _parse_spec_map may raise SpecParseError (propagates).
   # The clone ctx-mgr ensures temp-dir cleanup on every outcome, so it is safe
   # to do all diff work inside the with-block and return the merged EndpointDiff
   # (a pure value) afterwards.

5. if not merged.has_changes():
       report = ImpactReport(
           summary="No changes detected", risk="LOW",
           modified=[], affected=[], requirements=[], checklist=[])
       logger.info("plan completed: no changes")
       return render_impact_report(report)

6. changed = merged.changed_paths()
   affected = find_affected_endpoints(changed, graph)
   graph_context, trimmed_affected = _build_graph_context(affected, changed, graph)  # trimmed slice
   system = build_impact_report_system_prompt()
   user = build_impact_report_user_prompt(
       added=merged.added, removed=merged.removed, modified=merged.modified,
       affected=trimmed_affected, graph_context=graph_context)

7. client = build_llm_client()                                                # UnsupportedLLMProtocolError propagates
   raw = client.ask(system=system, user=user)                                 # LLMCallError / LLMRateLimitedError propagate
   report = _parse_impact_report(raw)                                         # LLMResponseParseError on bad JSON/shape

8. logger.info("plan completed", extra={"changed": len(changed), "affected": len(affected)})
   return render_impact_report(report)
```

Helpers (private, same file):

- `_parse_spec_map(paths, root) -> dict[str, dict]` — `{p.relative_to(root).as_posix(): parse_spec(p) for p in paths}`. Matching key is the POSIX relative path so the same spec under baseline and clone aligns.
- `_diff_and_classify(baseline, fresh) -> EndpointDiff` — for each `rel` in the union of keys:
  - both sides: `raw = diff_specs(baseline[rel], fresh[rel])`; `pair = classify_endpoint_changes(raw)`; merge `pair.added`/`removed`/`modified` into the running aggregate.
  - fresh-only (`rel` not in baseline): the whole spec was added → `added.extend(sorted(fresh[rel].get("paths", {}).keys()))`. Diffing against `{}` does NOT surface individual endpoints (deepdiff reports the top-level `paths` key), so paths are read directly from the parsed spec.
  - baseline-only (`rel` not in fresh): the whole spec was removed → `removed.extend(sorted(baseline[rel].get("paths", {}).keys()))`.
  Merge dedups `added`/`removed`; extends `modified[ep]`. Return the aggregate.
- `_build_graph_context(affected, changed, graph) -> tuple[dict[str, list[str]], list[str]]` — compute `kept`: if `len(affected) > _MAX_AFFECTED`, keep `changed` first (in their existing order) then the sorted remainder, truncated to `_MAX_AFFECTED`; log `WARNING "plan context truncated"`. Otherwise `kept = affected`. Return `(graph_context = {p: list(graph.edges.get(p, [])) for p in kept}, trimmed_affected = sorted(kept))`. `_MAX_AFFECTED = 100`. Both the prompt's `affected` array and `graph_context` are bounded by the kept set.
- `_parse_impact_report(raw) -> ImpactReport` — strip prose/fences (reuse the first-`{`-to-last-`}` slice convention from `run_discover`), `json.loads`, validate it is a `dict` with exactly the six keys, validate value types (`summary: str`, `risk: str`, `modified/affected/requirements/checklist: list[str]`), coerce `risk` to upper and if it is not in `{HIGH, MEDIUM, LOW}` set it to `MEDIUM` and `logger.warning("invalid risk, falling back to MEDIUM", extra={"risk": <raw>})`. On `json.JSONDecodeError` or any shape mismatch raise `LLMResponseParseError(reason=..., excerpt=raw[:200])`. Construct and return the `ImpactReport`.

**Errors:** does not catch `LLMCallError`, `LLMRateLimitedError`,
`LLMResponseParseError`, `UnsupportedLLMProtocolError`, `SpecParseError`,
`RepositoryCloneError`, `SpecsNotFoundError`, `TraceabilityGraphMissingError`,
`MissingEnvironmentVariablesError` — all propagate to the CLI handler.

**Edge Cases:**
- No matching spec pairs → empty `EndpointDiff` → no-change report.
- Spec present only on one side → its paths are read directly from the parsed spec
  (fresh-only → added, baseline-only → removed). Diffing a whole spec against `{}`
  would lose individual endpoints (deepdiff reports the top-level `paths` key).
- LLM returns risk outside the allowed set → fallback `MEDIUM` (WARNING).
- Large graph → deterministic trim, WARNING log; `build_impact_report_user_prompt`
  contract honored (caller trims).
- `SWAX_LLM_TOKEN` never logged and never present in the returned Markdown (the
  report is built only from `ImpactReport` fields, none of which is the token).

#### `ImpactReport`

pydantic model, `kw_only=True`, six `str` / `list[str]` fields. No methods.

#### `render_impact_report`

**Responsibility**: pure `ImpactReport → Markdown`.

**Algorithm:**
```
Render, in order:
  # Impact Report
  **Summary:** <report.summary>
  **Risk:** <report.risk>
  ## Modified Endpoints        — bullet list, or "- (none)" if empty
  ## Affected Endpoints        — bullet list, or "- (none)"
  ## Requirements              — bullet list, or "- (none)"
  ## Checklist                 — "- [ ] <item>" list, or "- (none)"
Return the joined string with a trailing newline.
```

**Edge Cases:** the no-change report renders identically to any other (Summary
"No changes detected", Risk LOW, four empty sections shown as "(none)").

### `swax/commands/plan/` — CLI handler

#### `plan`

**Responsibility**: delegate, echo, map errors.

**Algorithm:**
```
@click.command()
@click.pass_obj
def plan(ctx: SwaxContext) -> None:
    """Analyze spec changes and print the impact report."""
    project_root = pathlib.Path.cwd()
    try:
        markdown = run_plan(project_root)
    except MissingEnvironmentVariablesError as exc:
        raise click.ClickException(f"Missing env vars: {', '.join(exc.missing)}") from exc
    except SpecParseError as exc:
        raise click.ClickException(f"Failed to parse {exc.path}: {exc.reason}") from exc
    except RepositoryCloneError as exc:
        raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}") from exc
    except SpecsNotFoundError as exc:
        raise click.ClickException(f"Specs directory not found: {exc.path}") from exc
    except TraceabilityGraphMissingError as exc:
        raise click.ClickException(f"Traceability graph not found at {exc.path} — run `swax discover` first") from exc
    except LLMRateLimitedError as exc:
        raise click.ClickException("LLM rate limited; retry later") from exc
    except LLMCallError as exc:
        raise click.ClickException(f"LLM call failed: {exc.reason}") from exc
    except UnsupportedLLMProtocolError as exc:
        raise click.ClickException(f"Unsupported LLM protocol: {exc.protocol}") from exc
    except LLMResponseParseError as exc:
        raise click.ClickException(f"LLM response parse failed: {exc.reason}") from exc
    click.echo(markdown)
```

Imports `run_plan_handler as run_plan` from `...applications` (mirrors
`run_discover`), and `SwaxContext` under `TYPE_CHECKING` only (keeps the
`cli ↔ commands` edge acyclic — exactly as `discover.py` does).

**Edge Cases:** generic `Exception` is never caught; `SWAX_LLM_TOKEN` never
appears in any message.

### `swax/cli` — registration (already applied)

`__main__.py` already does (per the prior stage's user choice A):

```python
from ..commands import discover_handler, init_handler, plan_handler
from .main import main

main.add_command(discover_handler, name="discover")
main.add_command(init_handler, name="init")
main.add_command(plan_handler, name="plan")
```

The facade `swax/commands/__init__.py` must be updated to export `plan_handler`
(see Implementation Instructions).

---

## Cross-cutting Concerns

- **Error handling** — domain exceptions propagate from `run_plan` uncaught; the
  `plan` handler maps all nine to `click.ClickException` (exit code 1). `plan`
  never catches `Exception` broadly and never retries rate-limited calls.
  `run_plan` is the sole raiser of `TraceabilityGraphMissingError` (existence
  check) and `LLMResponseParseError` (defensive parse). No secrets in any error
  message or echoed output.
- **Logging** — `logging.getLogger(__name__)` (stdlib, per conventions). INFO at
  start/end of `run_plan`; DEBUG for intermediate steps (path counts, raw diff
  summary); WARNING on risk fallback and on context truncation. Structured
  `extra={...}` with machine-readable keys. `SWAX_LLM_TOKEN` is never in any log
  field. Lowercase, concise, stable event names.
- **Validation** — `require_vars` validates LLM creds; `load_config` validates
  the YAML; `_parse_impact_report` validates the LLM JSON shape and the risk
  enum; `EndpointDiff`/`ImpactReport` are pydantic models with `kw_only=True`.
- **Caching** — none. `plan` is a stateless single-pass analysis.
- **Concurrency** — single-threaded; no thread-safety requirements.
- **Resource cleanup** — the git clone lives inside `clone_specs`'s context
  manager (`tempfile.TemporaryDirectory`), so the temp dir is removed on every
  outcome including exceptions. All diff/classify work that needs the fresh
  clone happens inside the `with` block; only the pure `EndpointDiff` value
  escapes it.

---

## Usages Analysis

### Project-level Usages (`.goga/usages/`)

#### `conventions`
- **What it provides**: mandatory Python rules — relative intra-package imports,
  pydantic `kw_only=True`, Google-style docstrings, stdlib `logging` with
  structured `extra`, blank-line block separation, test structure mirroring
  source, `pytest`/`ruff` commands.
- **Where used**: every affected cell (global annotation in each).
- **Why chosen**: project-wide baseline; all swax cells already apply it.
- **How exactly**: relative imports for `...config`, `...git`, etc.; pydantic
  `ConfigDict(kw_only=True)` on `EndpointDiff` and `ImpactReport`; `logger =
  logging.getLogger(__name__)`; tests under `tests/<cell>/test_<module>_*`.

#### `deepdiff`
- **What it provides**: structural-diff API for two dicts (`DeepDiff(...,
  ignore_order=True, ...)`), change-set accessors (`dictionary_item_added`,
  `dictionary_item_removed`, `values_changed`, `type_changes`), perf knobs
  (`cutoff_intersection_for_pairs`, `verbose_level`), classification-by-path
  example, and a direct-assert test pattern.
- **Where used**: `swax/openapi` (`diff_specs`, `classify_endpoint_changes`).
- **Why chosen**: deterministic structural comparison of dereferenced specs;
  path-keyed change sets map cleanly onto endpoint classification.
- **How exactly**: `diff_specs` builds the `DeepDiff` with the documented kwargs;
  `classify_endpoint_changes` walks the change sets by path string. **Must add
  `deepdiff>=8.0` to `pyproject.toml` `[project.dependencies]`** (not yet
  present).

#### `click`
- **What it provides**: `@click.command()`, `@click.pass_obj`, `click.echo`,
  `click.ClickException`, and the `CliRunner` test pattern.
- **Where used**: `swax/commands/plan` (`plan`).
- **Why chosen**: the project's only CLI framework.
- **How exactly**: `plan` is a `@click.command()` + `@click.pass_obj` handler;
  every domain error becomes `click.ClickException`; tests use
  `click.testing.CliRunner`.

### Cell-level Usages (Imports → `.usages/`)

`run_plan` consumes six provider cells; the imported usage files are read for
implementation context (tracked cross-cell links, not contractual obligations):

- `project-config`, `environment` from `swax/config` — `load_config` / `Config`
  shape and `require_vars` semantics.
- `specs-repository` from `swax/git` — `clone_specs` context-manager contract and
  its two errors.
- `parsing`, `diff` from `swax/openapi` — `discover_specs` / `parse_spec` and the
  new `diff_specs` / `classify_endpoint_changes` / `EndpointDiff`.
- `graph-lifecycle`, `affected-endpoints` from `swax/traceability` —
  `load_traceability` / `TraceabilityGraph` and
  `find_affected_endpoints` / `TraceabilityGraphMissingError`.
- `impact-report-prompts` from `swax/prompts` — the two builder routines.
- `llm-transport` from `swax/llm` — `build_llm_client` / `LLMClient.ask` and the
  LLM error types.
- `cli-facade` from `swax/cli` (consumed by `commands/plan`) — the `SwaxContext`
  access pattern.
- `plan AS plan-usage` from `swax/applications` (consumed by `commands/plan`) —
  `run_plan` semantics.

### Inline Usages

- **`json`** (in `applications/plan`) — `json.loads` for the LLM response,
  `json.JSONDecodeError` wrapped into `LLMResponseParseError`; `json.dumps` (in
  `prompts`) to render the user-prompt blocks. Defensive parsing only.

---

## `.usages/` Update

The `apply-architecture` stage already created the five consumer-facing
`.usages` files below. They are **consistent** with the materialized CODEMANIFEST
(signatures, error tables, and assembly snippets match). No edits required.

### Cell: `swax/openapi`

- **`diff`** → `swax/openapi/.usages/diff.md` — Status: **current**. Covers
  `diff_specs`, `classify_endpoint_changes`, `EndpointDiff`, preconditions
  (dereferenced specs), and the test pattern. Aligned with the deepdiff cook.

### Cell: `swax/traceability`

- **`affected-endpoints`** → `swax/traceability/.usages/affected-endpoints.md` —
  Status: **current**. Covers `find_affected_endpoints`, `load_traceability`, the
  reverse-reachability model, and the missing-graph precondition
  (`TraceabilityGraphMissingError` raised by `run_plan`).

### Cell: `swax/prompts`

- **`impact-report-prompts`** → `swax/prompts/.usages/impact-report-prompts.md` —
  Status: **current**. Covers both builders and the no-secrets rule.

### Cell: `swax/applications` (facade)

- **`plan`** → `swax/applications/.usages/plan.md` — Status: **current**. The
  consumer usage for the `plan` use-case (lives at the facade; the sub-cell
  `applications/plan/` has no own `.usages`, like `applications/discover/`).

### Cell: `swax/commands` (facade)

- **`plan`** → `swax/commands/.usages/plan.md` — Status: **current**. Covers
  registration (`main.add_command(plan_handler, name="plan")`), execution, the
  nine-row error table, and the `CliRunner` test pattern.

---

## Test Stack Trace

Tests mirror the source structure under `tests/`, split into `*_contract.py`
(signature, docstring, `__all__`, facade re-exports) and `*_logic.py`
(behavior). External boundaries are mocked at the import point; pure logic is
mock-free. No live LLM is ever contacted.

### General Setup

- Env fixture: `SWAX_LLM_MODEL`, `SWAX_LLM_PROTOCOL`, `SWAX_LLM_BASE_URL`,
  `SWAX_LLM_TOKEN` set via `monkeypatch.setenv`.
- `tmp_path` project: write `.swax/config.yml`, `.swax/traceability.yml`, and
  baseline specs under `tmp_path / config.specs.location`.
- LLM boundary mocked at `swax.applications.plan.run_plan.build_llm_client` (and
  `clone_specs` at its import point when a real clone is undesirable).
- `deepdiff.DeepDiff` is deterministic — assert on it directly (no mock).

### Source File Registry

New files under test:
- `swax/openapi/{diff_specs,classify_endpoint_changes,endpoint_diff}.py`
- `swax/traceability/find_affected_endpoints.py`
- `swax/prompts/{build_impact_report_system_prompt,build_impact_report_user_prompt}.py`
- `swax/applications/plan/{run_plan,impact_report,render_impact_report}.py`
- `swax/commands/plan/plan.py`

---

### Positive Tests

#### `test_diff_specs_detects_added_endpoint`

**Setup**: two dereferenced spec dicts —
`base = {"paths": {"/users": {}}}`, `current = {"paths": {"/users": {}, "/orders": {}}}`.

**Input**: `diff_specs(base, current)`.

**Trace**:
```
diff_specs(base, current)
  → DeepDiff(base, current, ignore_order=True, report_repetition=False,
             cutoff_intersection_for_pairs=1, verbose_level=1)
    → change set dictionary_item_added contains a path under root['paths']['/orders']
classify_endpoint_changes(result)
  → _extract_endpoint(...) == "/orders"  → added.append("/orders")
  → EndpointDiff(added=["/orders"], removed=[], modified={})
assert "/orders" in changes.added
```

**Assertions**:
```
changes.added == ["/orders"]
changes.removed == []
changes.modified == {}
changes.has_changes() is True
"/orders" in changes.changed_paths()
```

**Sufficiency**: proves the diff + classification pipeline detects a newly added
endpoint and that `EndpointDiff` aggregates it correctly.

#### `test_run_plan_no_changes_skips_llm_and_returns_low_risk`

**Setup**: `tmp_path` with `.swax/config.yml` (git.url, git.location,
specs.location=`specs`), `.swax/traceability.yml` (one edge `/a -> /b`), and a
baseline spec under `tmp_path/specs/api.yaml`. `clone_specs` mocked to yield a
fresh root containing an **identical** copy of the spec. `build_llm_client`
mocked — must **not** be called.

**Input**: `run_plan(tmp_path)`.

**Trace**:
```
require_vars() → ok
load_config(tmp_path/".swax"/"config.yml") → Config
traceability.yml exists → load_traceability → graph
clone_specs(...) → fresh root (mock)
  parse baseline + fresh (identical) → diff_specs → empty DeepDiff
  classify_endpoint_changes → EndpointDiff(added=[], removed=[], modified={})
merged.has_changes() is False
  → ImpactReport(summary="No changes detected", risk="LOW", ...)
  → render_impact_report → Markdown
  → return (build_llm_client NEVER called)
```

**Assertions**:
```
"No changes detected" in markdown
"LOW" in markdown
mock_build_llm_client.assert_not_called()
```

**Sufficiency**: proves the no-change short-circuit skips the LLM and still
renders a valid report (acceptance criterion: no changes → Summary "No changes
detected", Risk LOW).

#### `test_plan_handler_echoes_markdown_and_maps_missing_graph`

**Setup**: `CliRunner`; `run_plan` mocked at
`swax.commands.plan.plan.run_plan` to (a) return a Markdown string, and (b) in a
second case raise `TraceabilityGraphMissingError(path=...)`.

**Input**: `runner.invoke(main, ["plan"])`.

**Trace**:
```
main group → load_env → SwaxContext
plan(ctx) → run_plan(Path.cwd()) [mocked]
  case a: returns "# Impact Report ..." → click.echo
  case b: raises TraceabilityGraphMissingError → click.ClickException(...)
```

**Assertions**:
```
case a: result.exit_code == 0 and "# Impact Report" in result.output
case b: result.exit_code == 1 and "Traceability graph not found" in result.output
        and "swax discover" in result.output
```

**Sufficiency**: proves the handler echoes Markdown on success and maps the
missing-graph error to the discover hint (acceptance criterion).

---

### Negative Tests

#### `test_run_plan_raises_missing_graph_when_traceability_absent`

**Setup**: `tmp_path` with `.swax/config.yml` but **no** `.swax/traceability.yml`.
`build_llm_client` and `clone_specs` mocked.

**Input**: `run_plan(tmp_path)`.

**Trace**:
```
require_vars() → ok
load_config → Config
traceability_path.exists() is False
  → raise TraceabilityGraphMissingError(path=tmp_path/".swax"/"traceability.yml")
```

**Assertions**:
```
with pytest.raises(TraceabilityGraphMissingError) as exc:
    run_plan(tmp_path)
assert exc.value.path.name == "traceability.yml"
```

**Sufficiency**: proves `run_plan` (not `load_traceability`) owns the
missing-graph check (acceptance criterion).

#### `test_run_plan_invalid_risk_falls_back_to_medium`

**Setup**: full `tmp_path` project; fresh spec differs from baseline (one added
endpoint); `build_llm_client` mocked to return a client whose `ask` returns a
JSON payload with `"risk": "EXTREME"`.

**Input**: `run_plan(tmp_path)`.

**Trace**:
```
diff → EndpointDiff(added=["/x"], ...) → has_changes() True
find_affected_endpoints → affected
build prompts → client.ask → raw JSON with risk="EXTREME"
_parse_impact_report: risk not in {HIGH,MEDIUM,LOW} → set "MEDIUM", WARNING
render_impact_report → Markdown
```

**Assertions**:
```
"MEDIUM" in markdown
"EXTREME" not in markdown
(caplog WARNING contains "risk")
```

**Sufficiency**: proves the risk-enum fallback to MEDIUM (risk-assessment
quality constraint).

#### `test_run_plan_propagates_llm_response_parse_error_on_bad_json`

**Setup**: as above, but `client.ask` returns `"not json at all"`.

**Input**: `run_plan(tmp_path)`.

**Trace**:
```
_parse_impact_report: no balanced braces → json.loads raises JSONDecodeError
  → raise LLMResponseParseError(reason=..., excerpt=...)
```

**Assertions**:
```
with pytest.raises(LLMResponseParseError): run_plan(tmp_path)
```

**Sufficiency**: proves defensive parsing wraps malformed LLM output into the
domain error (propagates to the handler).

---

### Edge Case Tests

#### `test_classify_endpoint_changes_attributes_schema_change_to_endpoint`

**Setup**: dereferenced specs where a schema field changed **and** the same
change is inlined under a consuming endpoint (post-dereference state):
`base` has `paths./users.get.responses.200.schema.type = "object"` and
`components.schemas.User.name`; `current` changes both the response type and the
schema field.

**Input**: `classify_endpoint_changes(diff_specs(base, current))`.

**Trace**:
```
walk values_changed:
  root['paths']['/users']['get']['responses']['200']['schema']['type'] → endpoint "/users", modified
  root['components']['schemas']['User']['name'] → _extract_endpoint None → skip
```

**Assertions**:
```
"/users" in changes.modified
assert all(ep.startswith("/") for ep in changes.modified)   # no schema-level paths leak
```

**Sufficiency**: proves schema changes are attributed to endpoints via
dereferencing and that no `components`/`definitions` path leaks as a report path
(acceptance criterion: schema changes attributed to using endpoints).

#### `test_endpoint_diff_changed_paths_dedup_across_buckets`

**Setup**: construct `EndpointDiff` directly with a path that appears in more than
one bucket and an empty diff for the `False` case:
`diff_a = EndpointDiff(added=["/x"], removed=[], modified={"/x": ["resp 200 changed"]})`;
`diff_b = EndpointDiff(added=[], removed=[], modified={})`.

**Input**: `diff_a.changed_paths()`, `diff_a.has_changes()`, `diff_b.has_changes()`.

**Trace**:
```
diff_a.changed_paths() -> sorted(set(["/x"]) | set([]) | set(["/x"])) == ["/x"]   # dedup, single entry
diff_a.has_changes()   -> bool(added or removed or modified) == True
diff_b.has_changes()   -> bool([] or [] or {}) == False
```

**Assertions**:
```
assert diff_a.changed_paths() == ["/x"]
assert diff_a.has_changes() is True
assert diff_b.has_changes() is False
```

**Sufficiency**: proves `changed_paths()` deduplicates a path shared across
`added`/`modified` and that `has_changes()` is `False` for an empty `EndpointDiff`
(the no-change short-circuit precondition in `run_plan`).


#### `test_find_affected_endpoints_reverse_reachability`

**Setup**: `TraceabilityGraph(edges={"/a": ["/b"], "/b": ["/c"], "/d": ["/c"]})`
— `/a` depends on `/b` depends on `/c`; `/d` also depends on `/c`.

**Input**: `find_affected_endpoints(["/c"], graph)`.

**Trace**:
```
reverse: /b ← [/a], /c ← [/b, /d]
BFS from /c: /c, then dependents /b and /d, then /b's dependent /a
affected = {/c, /b, /d, /a}
```

**Assertions**:
```
assert find_affected_endpoints(["/c"], graph) == ["/a", "/b", "/c", "/d"]
```

**Sufficiency**: proves transitive reverse reachability (acceptance criterion:
affected = direct + all transitive dependents).

#### `test_find_affected_endpoints_keeps_changed_path_not_in_graph`

**Setup**: `TraceabilityGraph(edges={"/a": ["/b"]})`.

**Input**: `find_affected_endpoints(["/zzz"], graph)`.

**Assertions**:
```
assert find_affected_endpoints(["/zzz"], graph) == ["/zzz"]
```

**Sufficiency**: proves a changed path absent from the graph is still returned
(contract requirement).

#### `test_render_impact_report_no_change_renders_consistently`

**Setup**: `ImpactReport(summary="No changes detected", risk="LOW", modified=[],
affected=[], requirements=[], checklist=[])`.

**Input**: `render_impact_report(report)`.

**Assertions**:
```
assert "No changes detected" in md
assert "LOW" in md
assert "(none)" in md            # empty sections render explicitly
```

**Sufficiency**: proves the no-change report renders identically to any other
(pure transformation, no synthesized content).

#### `test_plan_handler_maps_all_nine_domain_errors`

**Setup**: parametrize over the nine `(exception, message_fragment)` pairs from
the error table; `run_plan` mocked to raise each.

**Input**: `runner.invoke(main, ["plan"])`.

**Assertions**:
```
result.exit_code == 1
message_fragment in result.output
"SWAX_LLM_TOKEN" not in result.output
```

**Sufficiency**: proves the full 9-error mapping (acceptance criterion + no
token leakage).

---

## Additional Instructions for the Implementation Agent

The CODEMANIFEST contracts are clean (`goga lint` → 0 errors). The
implementation must produce exactly these files:

**Create (new):**
- `swax/openapi/diff_specs.py`, `classify_endpoint_changes.py`, `endpoint_diff.py`
- `swax/traceability/find_affected_endpoints.py`, `errors.py`
- `swax/prompts/build_impact_report_system_prompt.py`, `build_impact_report_user_prompt.py`
- `swax/applications/plan/__init__.py`, `run_plan.py`, `impact_report.py`, `render_impact_report.py`
- `swax/commands/plan/__init__.py`, `plan.py`

**Modify (existing — required for the new code to import):**
- `swax/openapi/__init__.py` — export `diff_specs`, `classify_endpoint_changes`, `EndpointDiff` (add to `__all__`).
- `swax/traceability/__init__.py` — export `find_affected_endpoints`, `TraceabilityGraphMissingError` (the new `errors.py` and `find_affected_endpoints.py` are Created above).
- `swax/prompts/__init__.py` — export the two new builders.
- `swax/applications/__init__.py` — add `from .plan import run_plan as run_plan_handler` and extend `__all__` (the `__main__.py` already imports `plan_handler` from the commands facade, so **both** facades must be updated or `swax plan` will `ImportError`).
- `swax/commands/__init__.py` — add `from .plan import plan as plan_handler` and extend `__all__`.
- `pyproject.toml` — add `deepdiff>=8.0` to `[project.dependencies]` (currently absent; the openapi CODEMANIFEST references the `deepdiff` usage and `diff_specs` imports it).

(`swax/cli/__main__.py` is already updated by the prior stage — do not change it.)

**Discipline:**
- Relative intra-package imports only; `SwaxContext` imported under
  `TYPE_CHECKING` in `plan.py` (mirror `discover.py`).
- pydantic `kw_only=True` on `EndpointDiff` and `ImpactReport`.
- Google-style docstrings on every public symbol; `__all__` in every module.
- `logging.getLogger(__name__)`; INFO start/end, DEBUG intermediate, WARNING on
  risk fallback and context truncation; never log `SWAX_LLM_TOKEN`.
- Tests mirror source under `tests/`, split `*_contract.py` / `*_logic.py`,
  plus facade re-export tests (`tests/applications/...`,
  `tests/commands/test_commands_facade.py`). Mock only at external boundaries
  (`build_llm_client`, `clone_specs`, `Repo.clone_from`).

**Validation gate (acceptance):**
- `ruff check swax/` clean.
- `pytest tests/ -x` green.
- `python -c "from swax.openapi import diff_specs, classify_endpoint_changes, EndpointDiff; from swax.traceability import find_affected_endpoints, TraceabilityGraphMissingError; from swax.prompts import build_impact_report_system_prompt, build_impact_report_user_prompt; from swax.applications import run_plan_handler; from swax.commands import plan_handler"` succeeds.
- `swax --env-file .env plan` (mocked LLM) prints Markdown; `swax plan` with no `.swax/traceability.yml` exits 1 with the `swax discover` hint.
