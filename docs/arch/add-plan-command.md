# Architecture Plan: Swax — `plan` command

## Topic

**Topic:** `add-plan-command` — архитектура команды `plan` (Задача 2 продукта Swax).
**Plan file:** `docs/arch/add-plan-command.md`

Команда `plan` анализирует различия между локальными (базовыми) спецификациями и текущим
состоянием репозитория, отображает изменения на граф отслеживаемости и формирует Markdown
Impact Report о влиянии изменений на тестирование (вывод в stdout).

План опирается на слоистую архитектуру из `docs/arch/1-init-and-discover.md`
(`cli → commands → applications → доменные cell-ы`) и описывает изменения (modify) и новые
cell-ы (create), необходимые для Задачи 2.

**Design decision (согласовано):** diff-подсистема реализуется как расширение существующего
плоского cell-а `swax/openapi` (вариант B), а не как отдельный дочерний cell.

---

## Implementation Order

Порядок реализации — от leaves к root (cell-ы без зависимостей — первыми), чтобы Imports
каждого cell-а разрешались в уже спроектированные контракты:

1. **`swax/openapi`** (modified) — нет Imports; добавляет diff-подсистему. База для `applications/plan`.
2. **`swax/traceability`** (modified) — нет Imports; добавляет обход графа + ошибку отсутствия графа.
3. **`swax/prompts`** (modified) — нет Imports; добавляет билдеры промпта Impact Report.
4. **`swax/applications/plan`** (created) — зависит от `config`, `git`, `openapi`, `traceability`, `prompts`, `llm` (все уже существуют/спроектированы в пп. 1–3).
5. **`swax/applications`** (modified facade) — зависит от `applications/plan` (п. 4).
6. **`swax/commands/plan`** (created) — зависит от `applications` (facade), `cli` и доменных error-cell-ов.
7. **`swax/commands`** (modified facade) — зависит от `commands/plan` (п. 6).
8. **`swax/cli`** (modified) — зависит только от `config`; лениво регистрирует `plan` в `__main__.py`.

---

## Artifacts

### Cell 1/8: `swax/openapi/` (modified)

Расширение существующего плоского cell-а: добавляется usage `deepdiff`, расширяется глобальная
annotation и добавляются 3 новых типа (`diff_specs`, `classify_endpoint_changes`, `EndpointDiff`).
Существующие типы (`parse_spec`, `extract_paths`, `extract_schemas`, `discover_specs`,
`SpecParseError`) остаются без изменений.

#### CODEMANIFEST: `swax/openapi/CODEMANIFEST` (diff)

**Usages — add:**
```yaml
  deepdiff: .goga/usages/cooks/deepdiff.md
```

**Annotations — extend** (добавить в существующую глобальную annotation):
```yaml
  Parsing of OpenAPI/Swagger specifications and extraction of paths and schemas
  for the traceability graph, plus structural diffing of two dereferenced specs
  and classification of endpoint/schema changes.
  The diff sees methods/parameters/schemas for analysis only — classified changes
  surface as paths with descriptions, never as method/schema-level entries.
  Use `deepdiff` for structural diffing of two dereferenced specs.
```

**Body — add (3 new type declarations):**
```yaml
"diff_specs(base: dict, current: dict) -> diff: DeepDiff":
  location: diff_specs.py
  annotations: |
    Computes a structural diff between two dereferenced specifications.

    `base`: baseline (local) spec dict — output of `parse_spec`.
    `current`: fresh (cloned repo) spec dict — output of `parse_spec`.
    `diff`: a DeepDiff result consumed by `classify_endpoint_changes`.

    Algorithm:
    1. Build a `DeepDiff` over `base` and `current` with ignore_order and the cutoff option from `deepdiff`.
    2. Return the result unchanged — classification happens in `classify_endpoint_changes`.

    Requirements:
    - Both inputs are fully dereferenced (Prance already inlined `$ref` via `parse_spec`).
    - List order is ignored — endpoint order is not significant.

    Constraints:
    - Do not classify changes here — this routine only computes the raw structural diff.
    - Avoid verbose_level=2 in the production path.

"classify_endpoint_changes(diff: DeepDiff) -> changes: EndpointDiff":
  location: classify_endpoint_changes.py
  annotations: |
    Classifies a raw structural diff into endpoint-level changes.

    `diff`: DeepDiff result from `diff_specs`.
    `changes`: an `EndpointDiff` aggregating added, removed, and modified endpoints with schema detail.

    Algorithm:
    1. Walk the diff change sets (keys_added, keys_removed, values_changed) by their path strings.
    2. Paths under `paths` become endpoint changes: added / removed / modified.
    3. Paths under `components`/`definitions` are schema changes — because `$ref` is already
       dereferenced, each affected endpoint surfaces the change directly; attribute it to that endpoint.
    4. Aggregate multiple changes on the same path into a single modified entry with a list of descriptions.
    5. Return the `EndpointDiff`.

    Requirements:
    - Swagger 2.0 (definitions) and OpenAPI 3.x (components.schemas) handled transparently.
    - Modified entries carry human-readable change descriptions for the Impact Report.

    Constraints:
    - Do not emit method-level or schema-level entries as separate paths — paths only.
    - Do not introduce endpoints outside the union of `base` and `current` path keys.

"EndpointDiff(added: list[str], removed: list[str], modified: dict[str, list[str]])":
  location: endpoint_diff.py
  annotations: |
    Classified change result between baseline and current specifications.

    `added`: endpoint paths present in `current` but not in `base`.
    `removed`: endpoint paths present in `base` but not in `current`.
    `modified`: endpoint path -> list of human-readable change descriptions.
  properties:
    "added -> list[str]": |
      Endpoint paths present in `current` but not in `base`.
    "removed -> list[str]": |
      Endpoint paths present in `base` but not in `current`.
    "modified -> dict[str, list[str]]": |
      Endpoint path -> list of human-readable change descriptions.
  methods:
    "has_changes() -> changed: bool": |
      True when any endpoint was added, removed, or modified.
    "changed_paths() -> paths: list[str]": |
      Union of added, removed, and modified endpoint paths — sorted and deduplicated.
      Deterministic; each path appears once.
```

**Footer — extend Description:**
```yaml
  OpenAPI/Swagger parsing via Prance, extraction of paths and schemas for the
  traceability graph, and structural diffing/classification of endpoint changes.
```

#### .usages file: `swax/openapi/.usages/diff.md` (created)

````md
# Structural diff — comparing two dereferenced specs

## Domain

Patterns for computing and classifying a structural diff between a baseline and a fresh
specification. Target audience: cell `applications/plan/` (`run_plan` consumes `diff_specs`,
`classify_endpoint_changes`, and `EndpointDiff`).

Diff operates on fully dereferenced specs — Prance already inlined `$ref` during parsing.
The traceability graph stores paths only; diff granularity is for analysis.

## Computing a diff

```python
from swax.openapi import diff_specs, classify_endpoint_changes

raw = diff_specs(base_spec, current_spec)
changes = classify_endpoint_changes(raw)
```

`diff_specs` returns a `DeepDiff`; `classify_endpoint_changes` turns it into an `EndpointDiff`.

## Reading EndpointDiff

- `changes.added` / `changes.removed` — `list[str]` of endpoint paths.
- `changes.modified` — `dict[str, list[str]]`: path -> change descriptions.
- `changes.has_changes()` — skip the LLM when nothing changed.
- `changes.changed_paths()` — the endpoint set to map onto the graph.

## Preconditions

Both specs must come from `parse_spec` (dereferenced). Schema changes under
`components`/`definitions` are attributed to the endpoints that reference them automatically.
````

---

### Cell 2/8: `swax/traceability/` (modified)

Добавляется обход графа для затронутых эндпоинтов и доменная ошибка отсутствия графа.
Существующие типы (`TraceabilityGraph`, `load_traceability`, `save_traceability`) без изменений.
Header (`Usages`: conventions, pyyaml) без изменений. Cell остаётся без Imports
(`find_affected_endpoints` принимает `list[str]` — нет зависимости от `openapi`).

#### CODEMANIFEST: `swax/traceability/CODEMANIFEST` (diff)

**Body — add (2 new type declarations):**
```yaml
"find_affected_endpoints(changed_paths: list[str], graph: TraceabilityGraph) -> affected: list[str]":
  location: find_affected_endpoints.py
  annotations: |
    Finds all endpoints transitively affected by a set of changed endpoints via the traceability graph.

    `changed_paths`: endpoints that changed directly (e.g. `EndpointDiff.changed_paths()`).
    `graph`: the loaded traceability graph.
    `affected`: the changed endpoints plus every endpoint that transitively depends on them, sorted and deduplicated.

    Algorithm:
    1. Treat graph edges as source -> targets-it-depends-on (source depends on target);
       a node's dependents are the nodes whose adjacency list contains it.
    2. For each changed path, collect it and every node that transitively reaches it (reverse reachability).
    3. Merge, deduplicate, sort.

    Requirements:
    - Returns the complete affected set — no internal cap.
    - Changed paths not present as graph nodes are still returned.

    Constraints:
    - Read-only — does not mutate the graph.
    - Does not import from `openapi`; accepts plain path strings so the cell stays dependency-free.

"TraceabilityGraphMissingError(path: pathlib.Path)":
  location: errors.py
  annotations: |
    Raised when the traceability graph file does not exist — the project has not run `discover` yet.

    `path`: expected path to .swax/traceability.yml.
```

**Footer — extend Description** (mention traversal + missing-graph error).

#### .usages file: `swax/traceability/.usages/affected-endpoints.md` (created)

````md
# Affected endpoints — graph-based impact mapping

## Domain

How to compute the endpoints transitively affected by a set of changed paths. Target audience:
cell `applications/plan/` (`run_plan`).

The graph stores source -> its dependencies. A changed endpoint affects itself plus everyone who
(transitively) depends on it (reverse reachability: every node that reaches the changed node via
depends-on edges).

## Mapping changes to affected endpoints

```python
from swax.traceability import find_affected_endpoints, load_traceability

graph = load_traceability(traceability_path)
affected = find_affected_endpoints(changed_paths=changes.changed_paths(), graph=graph)
```

`affected` is a sorted, deduplicated `list[str]` covering the full transitive closure.

## Preconditions

The graph must exist — a missing file should surface as `TraceabilityGraphMissingError`
(raised by `run_plan`). The routine is read-only and accepts plain path strings.
````

---

### Cell 3/8: `swax/prompts/` (modified)

Добавляются 2 routine-билдера промпта Impact Report. Существующие билдеры графа без изменений.
Header (`Usages`: conventions) без изменений. Cell остаётся без Imports (передаются примитивы).

#### CODEMANIFEST: `swax/prompts/CODEMANIFEST` (diff)

**Annotations — extend** (упомянуть сценарий Impact Report).

**Body — add (2 new routines):**
```yaml
"build_impact_report_system_prompt() -> prompt: str":
  location: build_impact_report_system_prompt.py
  annotations: |
    Builds the system prompt that instructs the LLM to act as an API change impact analyst.

    `prompt`: the system message for the single-turn `LLMClient.ask` call in `run_plan`.

    Requirements:
    - Defines the LLM role: assess the testing impact of API endpoint changes.
    - Mandates the output contract: JSON with summary, risk, modified, affected, requirements, checklist.
    - Fixes allowed risk values to HIGH, MEDIUM, LOW.
    - Forbids prose around JSON — the response must be parseable as JSON.

    Constraints:
    - No parameters — the system prompt is constant for the plan use-case.
    - No endpoint data or graph — those go into the user prompt.
    - Never embed filesystem paths, tokens, or secrets.

"build_impact_report_user_prompt(added: list[str], removed: list[str], modified: dict[str, list[str]], affected: list[str], graph_context: dict[str, list[str]]) -> prompt: str":
  location: build_impact_report_user_prompt.py
  annotations: |
    Builds the user prompt: structured change context plus affected endpoints and the relevant graph portion.

    `added`/`removed`: endpoint path lists. `modified`: path -> change descriptions.
    `affected`: transitively affected endpoints. `graph_context`: relevant graph edges (path -> dependents).
    `prompt`: the user message for `LLMClient.ask`.

    Algorithm:
    1. Render `added`/`removed`/`affected` as JSON arrays.
    2. Render `modified`/`graph_context` as JSON objects.
    3. Instruct the LLM to return the Impact Report JSON contract from the system prompt.

    Requirements:
    - Output format matches the parser in `run_plan`.
    - Endpoint order follows the sorted order supplied by the caller.

    Constraints:
    - Do not truncate silently — the caller trims before calling if the context is large.
    - Never embed filesystem paths, tokens, or secrets.
```

#### .usages file: `swax/prompts/.usages/impact-report-prompts.md` (created)

````md
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
````

---

### Cell 4/8: `swax/applications/plan/` (created anew)

Новый use-case cell по шаблону `applications/discover/`. Владеет своим выходным контрактом
(`ImpactReport`, `render_impact_report`) и оркестратором `run_plan`.

#### CODEMANIFEST: `swax/applications/plan/CODEMANIFEST` (created)

```yaml
Imports:
  - Types:
      - load_config
      - require_vars
      - Config
    Usages:
      - project-config
      - environment
    From: swax/config
  - Types:
      - clone_specs
      - RepositoryCloneError
      - SpecsNotFoundError
    Usages:
      - specs-repository
    From: swax/git
  - Types:
      - discover_specs
      - parse_spec
      - diff_specs
      - classify_endpoint_changes
      - EndpointDiff
    Usages:
      - parsing
      - diff
    From: swax/openapi
  - Types:
      - load_traceability
      - TraceabilityGraph
      - find_affected_endpoints
      - TraceabilityGraphMissingError
    Usages:
      - graph-lifecycle
      - affected-endpoints
    From: swax/traceability
  - Types:
      - build_impact_report_system_prompt
      - build_impact_report_user_prompt
    Usages:
      - impact-report-prompts
    From: swax/prompts
  - Types:
      - build_llm_client
      - LLMClient
      - LLMCallError
      - LLMRateLimitedError
      - LLMResponseParseError
    Usages:
      - llm-transport
    From: swax/llm

Usages:
  conventions: .goga/usages/conventions.md
  json: |
    Python stdlib json module. Use json.loads for parsing LLM responses and
    catch json.JSONDecodeError to wrap into a domain error. Defensive parsing only —
    never trust LLM output structure without schema validation.

Annotations: |
  Application-layer use-case: generate an Impact Report by diffing baseline vs fresh specs,
  mapping changes onto the traceability graph, and asking the LLM once.
  The graph stores paths only; the diff sees methods/schemas for analysis but the report
  carries paths with change descriptions. Domain exceptions propagate uncaught — the CLI
  handler maps them: `RepositoryCloneError` and `SpecsNotFoundError` from `clone_specs`,
  and `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError` from the LLM call.
  `TraceabilityGraphMissingError` is raised when .swax/traceability.yml is absent (hint: run discover).
  Logs INFO at start/end, DEBUG for intermediate steps; SWAX_LLM_TOKEN never in logs.

  LLM responses are parsed defensively (provider-agnostic):
  - Strip prose/code fences around the JSON payload before parsing.
  - json.JSONDecodeError is wrapped into `LLMResponseParseError` with a raw payload excerpt.
  - The parsed shape is validated against the Impact Report contract; mismatch -> `LLMResponseParseError`.
  - The risk field is validated against {HIGH, MEDIUM, LOW}; an invalid value falls back to MEDIUM (WARNING log).

  Use `conventions` for code writing rules and testing.
  Use `project-config` for `load_config` and the `Config` shape.
  Use `environment` for `require_vars`.
  Use `specs-repository` for `clone_specs` and its errors (`RepositoryCloneError`, `SpecsNotFoundError`).
  Use `parsing` for `discover_specs` and `parse_spec`.
  Use `diff` for `diff_specs`, `classify_endpoint_changes`, and `EndpointDiff`.
  Use `graph-lifecycle` for `load_traceability` and `TraceabilityGraph`.
  Use `affected-endpoints` for `find_affected_endpoints` and `TraceabilityGraphMissingError`.
  Use `impact-report-prompts` for prompt assembly.
  Use `llm-transport` for `build_llm_client`, `LLMClient.ask`, and `LLMResponseParseError`.
  Use `json` for defensive parsing of the LLM JSON response.

---

"run_plan(project_root: pathlib.Path) -> markdown: str":
  location: run_plan.py
  annotations: |
    Use-case "plan": analyze differences between baseline and fresh specifications and produce an Impact Report.

    `project_root`: root of the Swax project — .swax/config.yml describes specs/repo, .swax/traceability.yml is read.
    `markdown`: the Impact Report rendered as Markdown for stdout.

    Algorithm:
    1. Validate LLM credentials via `require_vars`.
    2. Read `Config` via `load_config` — repo URL, specs location, local baseline root.
    3. Load the traceability graph via `load_traceability`; if the file is absent, raise `TraceabilityGraphMissingError`.
    4. Clone the repository via `clone_specs` (context manager) and parse the fresh specs (`discover_specs` + `parse_spec`).
    5. Parse the baseline specs from the local root (`discover_specs` + `parse_spec`).
    6. For each matching spec file pair, compute `diff_specs` then `classify_endpoint_changes`; merge into one `EndpointDiff`.
    7. If `EndpointDiff.has_changes()` is false, build a no-change `ImpactReport` (summary "No changes detected", risk LOW) and skip the LLM.
    8. Otherwise map via `find_affected_endpoints(changed_paths, graph)` and extract the relevant `graph_context`.
       If the affected set or `graph_context` exceeds a reasonable threshold, trim to the most relevant entries
       (changed paths first, then nearest dependents) and log a WARNING that the LLM context was truncated —
       honoring the `build_impact_report_user_prompt` contract that the caller trims. Then build system + user prompts.
    9. Call `LLMClient.ask` once, defensively parse JSON into an `ImpactReport`, validate risk (fallback MEDIUM).
    10. Render via `render_impact_report` and return the Markdown.

    Requirements:
    - The repository clone is cleaned up on every outcome (clone_specs context manager).
    - Baseline and fresh specs are matched by relative path.
    - Risk is constrained to {HIGH, MEDIUM, LOW} with a MEDIUM fallback.
    - SWAX_LLM_TOKEN never appears in logs or the returned Markdown.

    Constraints:
    - Do not catch `LLMCallError` / `LLMRateLimitedError` / `LLMResponseParseError` — let them propagate.
    - Do not store schemas or methods as separate report paths — paths with change descriptions only.
    - Do not print to stdout — return the Markdown; the CLI handler echoes it.

"ImpactReport(summary: str, risk: str, modified: list[str], affected: list[str], requirements: list[str], checklist: list[str])":
  location: impact_report.py
  annotations: |
    Structured LLM output for the Impact Report.

    `summary`: one-line human-readable summary of the change impact.
    `risk`: overall risk level — HIGH, MEDIUM, or LOW (validated by `run_plan`).
    `modified`: endpoint paths that changed.
    `affected`: endpoint paths transitively affected via the graph.
    `requirements`: testing requirements derived from the changes.
    `checklist`: actionable verification checklist items.
  properties:
    "summary -> str": |
      One-line human-readable summary of the change impact.
    "risk -> str": |
      Overall risk level — HIGH, MEDIUM, or LOW (validated by `run_plan`).
    "modified -> list[str]": |
      Endpoint paths that changed.
    "affected -> list[str]": |
      Endpoint paths transitively affected via the graph.
    "requirements -> list[str]": |
      Testing requirements derived from the changes.
    "checklist -> list[str]": |
      Actionable verification checklist items.

"render_impact_report(report: ImpactReport) -> markdown: str":
  location: render_impact_report.py
  annotations: |
    Renders an `ImpactReport` into the Markdown template for stdout.

    `report`: the impact report model (LLM-generated or the no-change placeholder).
    `markdown`: the report as Markdown following the template (Summary, Risk, Modified, Affected, Requirements, Checklist).

    Requirements:
    - Follows the report template from the product spec.
    - Renders the no-change report ("No changes detected", LOW) identically to any other report.

    Constraints:
    - Pure transformation — no I/O, no LLM calls.
    - Do not synthesize content not present in `report`.

---

Author: Goga
CreatedAt: 30/07/26
Description: |
  Application-layer use-case for change-impact analysis: diff baseline vs fresh specs,
  map changes onto the traceability graph, and generate a Markdown Impact Report via a single LLM call.
```

#### .usages file: `swax/applications/.usages/plan.md` (created)

*Sub-cell `applications/plan/` не имеет собственных `.usages` (как `applications/discover/`) —
consumer-usage живёт на уровне facade.*

````md
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
````

---

### Cell 5/8: `swax/applications/` (modified facade)

Добавляется re-export `run_plan_handler`.

#### CODEMANIFEST: `swax/applications/CODEMANIFEST` (diff)

**Imports — add:**
```yaml
  - Types:
      - run_plan AS run_plan_handler
    From: swax/applications/plan
```

**Annotations — extend:** упомянуть `run_plan_handler` в списке re-export и `plan` в списке практик.

**Body — add embedding:**
```yaml
->run_plan_handler: {}
```

---

### Cell 6/8: `swax/commands/plan/` (created anew)

Новый Click-handler cell по шаблону `commands/discover/`.

#### CODEMANIFEST: `swax/commands/plan/CODEMANIFEST` (created)

```yaml
Imports:
  - Types:
      - SwaxContext
    Usages:
      - cli-facade
    From: swax/cli
  - Types:
      - run_plan
    Usages:
      - plan AS plan-usage
    From: swax/applications
  - Types:
      - MissingEnvironmentVariablesError
    Usages:
      - environment
    From: swax/config
  - Types:
      - SpecParseError
    Usages:
      - parsing
    From: swax/openapi
  - Types:
      - RepositoryCloneError
      - SpecsNotFoundError
    Usages:
      - specs-repository
    From: swax/git
  - Types:
      - TraceabilityGraphMissingError
    Usages:
      - affected-endpoints
    From: swax/traceability
  - Types:
      - LLMCallError
      - LLMRateLimitedError
      - LLMResponseParseError
      - UnsupportedLLMProtocolError
    Usages:
      - llm-transport
    From: swax/llm

Usages:
  conventions: .goga/usages/conventions.md
  click: .goga/usages/cooks/click.md

Annotations: |
  Thin CLI handler: exception mapping only. All orchestration lives in `run_plan`.
  Every domain exception is mapped to click.ClickException with a user-facing message.
  The returned Markdown is echoed to stdout.

  Use `conventions` for code writing rules and testing.
  Use `click` for the command decorator, echo, and error mapping.
  Use `plan-usage` for `run_plan` semantics.
  Use `environment` for `MissingEnvironmentVariablesError`.
  Use `parsing` for `SpecParseError`.
  Use `specs-repository` for `RepositoryCloneError` and `SpecsNotFoundError`.
  Use `affected-endpoints` for `TraceabilityGraphMissingError`.
  Use `llm-transport` for the LLM error types.
  Use `cli-facade` for the `SwaxContext` access pattern.

---

"plan(ctx: click.Context)":
  location: plan.py
  annotations: |
    Click handler for the plan command: delegates to `run_plan`, echoes the report, and maps domain exceptions to user-facing errors.

    `ctx`: Click context whose obj is a `SwaxContext`.

    Algorithm:
    1. Resolve ctx.obj as `SwaxContext` via @click.pass_obj.
    2. Resolve project_root from the current working directory.
    3. Delegate to `run_plan` inside a try.
    4. Echo the returned Markdown to stdout.
    5. Map every documented domain exception to click.ClickException: `MissingEnvironmentVariablesError`,
       `SpecParseError`, `RepositoryCloneError`, `SpecsNotFoundError`, `TraceabilityGraphMissingError`,
       `LLMRateLimitedError`, `LLMCallError`, `UnsupportedLLMProtocolError`, `LLMResponseParseError`.

    Requirements:
    - No interactive prompts — plan reads everything from .swax/config.yml and the environment.
    - Exit code 0 on success, 1 on any ClickException.

    Constraints:
    - Do not catch generic Exception — only the documented domain exceptions.
    - Do not retry rate-limited calls.
    - SWAX_LLM_TOKEN never appears in any error message or echoed output.

---

Author: Goga
CreatedAt: 30/07/26
Description: |
  Click handler for the plan command — delegates to run_plan, echoes the report, and maps
  domain errors to ClickException.
```

#### .usages file: `swax/commands/.usages/plan.md` (created)

````md
# Plan command — Click handler for the `plan` command

## Domain

Registration and invocation template for the `plan` Click command. Target audience: cell
`swax/cli/` (registers the command on the `main` group via `main.add_command(plan)`).

The command is thin — only echo + error mapping. Application logic (clone, diff, mapping, LLM,
render) is delegated to `run_plan` (cell `applications/plan/`). No interactive prompts.

## Command registration

```python
from swax.cli import main
from swax.commands.plan import plan

main.add_command(plan)
```

Consumer conventions:
- The command takes no CLI options and has no prompts.
- The context is passed via `@click.pass_obj` — `SwaxContext` from the `cli/` cell.
- Requires a pre-loaded `.env` (the `main` group callback has already invoked `load_env`).

## Command execution

On `swax plan`, the command:
1. Receives `SwaxContext` via `@click.pass_obj`.
2. Resolves `project_root = pathlib.Path.cwd()`.
3. Delegates to `run_plan(project_root)` and echoes the returned Markdown to stdout.
4. Catches domain exceptions and maps them to `click.ClickException`.

## Error handling

| Exception | Message |
|---|---|
| MissingEnvironmentVariablesError | Missing env vars: {missing} |
| SpecParseError | Failed to parse {path}: {reason} |
| RepositoryCloneError | Failed to clone {url}: {reason} |
| SpecsNotFoundError | Specs directory not found: {path} |
| TraceabilityGraphMissingError | Traceability graph not found at {path} — run `swax discover` first |
| LLMRateLimitedError | LLM rate limited; retry later |
| LLMCallError | LLM call failed: {reason} |
| UnsupportedLLMProtocolError | Unsupported LLM protocol: {protocol} |
| LLMResponseParseError | LLM response parse failed: {reason} |

Exit codes: 0 — success, 1 — failure (Click default for `ClickException`).

## Testing

Test via `click.testing.CliRunner`, mocking `run_plan` at its import point. Assert `exit_code`
and echoed Markdown. Never call the live LLM API — always mock `run_plan`.
````

---

### Cell 7/8: `swax/commands/` (modified facade)

Добавляется re-export `plan_handler`.

#### CODEMANIFEST: `swax/commands/CODEMANIFEST` (diff)

**Imports — add:**
```yaml
  - Types:
      - plan AS plan_handler
    From: swax/commands/plan
```

**Annotations — extend:** упомянуть `plan_handler` в списке re-export и `plan` в практиках.

**Body — add embedding:**
```yaml
->plan_handler: {}
```

---

### Cell 8/8: `swax/cli/` (modified)

CODEMANIFEST не получает новых Imports/Types (регистрация остаётся ленивой, контракт ацикличен:
commands импортирует из cli, а не наоборот).

#### CODEMANIFEST: `swax/cli/CODEMANIFEST` (diff)

**`main` annotation — extend:** "Subcommands init, discover, and plan are registered in
`__main__.py`, not in this callback."

**Global Annotations — extend:** "Subcommands init, discover, and plan are registered lazily
to keep the CODEMANIFEST contract acyclic …".

#### Implementation: `swax/cli/__main__.py` (modified)

Регистрация команды `plan` (вне CODEMANIFEST-контракта):

```python
from swax.commands.plan import plan

main.add_command(plan)
```

---

## Dependency Map

```
swax/config · swax/git · swax/openapi · swax/traceability · swax/prompts · swax/llm   (domain leaves, import-free)
                 │           │                │                   │
                 └───────────┴────────────────┴───────────────────┴── all imported by ──┐
                                                                                          ▼
                                                                             swax/applications/plan
                                                                                          │ (run_plan AS run_plan_handler)
                                                                                          ▼
                                                                             swax/applications  (facade)
                                                                                          ▲
   swax/cli ──(SwaxContext)──────────────────────────── swax/commands/plan ──(plan AS plan_handler)── swax/commands (facade)
                                                                          ▲
   config(MissingEnvironmentVariablesError) · openapi(SpecParseError) ·   │
   git(RepositoryCloneError, SpecsNotFoundError) ·                         │
   traceability(TraceabilityGraphMissingError) · llm(LLM errors) ──────────┘

   swax/cli/__main__.py лениво регистрирует plan (main.add_command(plan)) — вне контракта, разрывает цикл cli↔commands.
```

Imports-соединения:
- `applications/plan` ← config, git, openapi, traceability, prompts, llm.
- `applications` (facade) ← applications/plan.
- `commands/plan` ← applications (run_plan), cli (SwaxContext), и error-типы из config/openapi/git/traceability/llm.
- `commands` (facade) ← commands/plan.
- `cli` ← config; регистрация plan ленивая в `__main__.py`.

Циклов нет.

---

## Verification Checklist

После реализации проверить:

**`swax/openapi`**
- `deepdiff` подключён в `Usages` и упомянут в global annotation.
- `diff_specs`, `classify_endpoint_changes`, `EndpointDiff` имеют `location` без подкаталогов и расширение `.py`.
- `EndpointDiff` — Entity (есть `properties` и `methods`).
- `goga lint swax/openapi` без ошибок.

**`swax/traceability`**
- `find_affected_endpoints` принимает `list[str]` + `TraceabilityGraph` (без импорта из `openapi`).
- `TraceabilityGraphMissingError` в `errors.py`.

**`swax/prompts`**
- Оба билдера возвращают `prompt: str`; cell остался без Imports.
- Никаких путей/токенов в промптах.

**`swax/applications/plan`**
- Все 6 `Imports` корректны; `EndpointDiff` импортирован из `openapi`.
- `run_plan` возвращает `markdown: str`; LLM-ошибки распространяются без перехвата.
- `ImpactReport` — Entity со всеми 6 свойствами; `render_impact_report` — pure transformation.
- Facade-импорт `run_plan AS run_plan_handler` + embedding `->run_plan_handler: {}`.

**`swax/commands/plan`**
- `run_plan` импортирован через `swax/applications` (facade) с алиасом usage `plan AS plan-usage`.
- `plan(ctx)` мапит все 9 доменных исключений → `ClickException`; эхо Markdown в stdout.
- Facade-импорт `plan AS plan_handler` + embedding `->plan_handler: {}`.

**`swax/cli`**
- В `__main__.py` добавлены `from swax.commands.plan import plan` и `main.add_command(plan)`.
- CODEMANIFEST остаётся без Imports из `commands` (ацикличность сохранена).

**Общее (по acceptance criteria):**
- `pytest tests/ -x` проходит (тесты зеркалят `tests/openapi/test_diff*`, `tests/traceability/test_find_affected_endpoints*`, `tests/applications/plan/test_run_plan*`, `tests/commands/plan/test_plan*`).
- `ruff check swax/` без ошибок.
- Проверка фасадов: `python -c "from swax.applications import run_plan_handler; from swax.commands import plan_handler"`.
- CLI smoke: `swax --env-file .env plan` (с моком LLM) выводит Markdown; `swax plan` без `.swax/traceability.yml` → ошибка с подсказкой `discover`.
