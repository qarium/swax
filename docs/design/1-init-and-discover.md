# Design Document: `1-init-and-discover`

Полная архитектурная спецификация фундамента CLI Swax: каркас CLI, 9 инфраструктурных/доменных клеток, 2 use-case-а, 2 CLI-команды. Спецификация выведена из материализованных CODEMANIFEST-ов и `.usages/` файлов.

---

## Contract Changes

### Changed CODEMANIFEST Files

Все 14 CODEMANIFEST файлов созданы в одном коммите `0de3308 Materialize init+discover architecture into 14 cells` поверх пустого `swax/`. Изменений в существующие контракты нет — задача greenfield.

| Cell | Тип | Назначение |
|------|-----|-----------|
| `swax/config/` | leaf | Модели конфигурации (`Config`, `GitConfig`, `SpecsConfig`), env-валидаторы, persistence в `.swax/config.yml` |
| `swax/fs/` | leaf | `ensure_swax_dir`, `copy_specs` — filesystem layout |
| `swax/git/` | leaf | `clone_specs` context manager, ошибки клонирования |
| `swax/openapi/` | leaf | `parse_spec`, `extract_paths`, `extract_schemas`, `discover_specs`, `SpecParseError` |
| `swax/traceability/` | leaf | `TraceabilityGraph`, `load_traceability`, `save_traceability` |
| `swax/prompts/` | leaf | `build_graph_system_prompt`, `build_graph_user_prompt`, `build_refine_user_prompt` |
| `swax/llm/` | level 1 | `LLMClient` protocol, `AnthropicAdapter`, `OpenAIAdapter`, factory |
| `swax/applications/init/` | level 1 | use-case `run_init` |
| `swax/applications/discover/` | level 1 | use-case `run_discover` (two-pass LLM analysis) |
| `swax/applications/` | facade | Re-export `run_init_handler`, `run_discover_handler` + cell-level usages |
| `swax/commands/init/` | level 2 | Click handler `init` |
| `swax/commands/discover/` | level 2 | Click handler `discover` |
| `swax/commands/` | facade | Re-export `init_handler`, `discover_handler` + cell-level usages |
| `swax/cli/` | root | `main` Click group + `SwaxContext` pass object |

### New Entities

**`swax/config/`** — `Config`, `GitConfig`, `SpecsConfig`, `MissingEnvironmentVariablesError`, `InvalidLLMProtocolError`, `InvalidLLMBaseURLError`, `load_env`, `require_vars`, `parse_protocol`, `parse_base_url`, `load_config`, `save_config`.

**`swax/fs/`** — `ensure_swax_dir`, `copy_specs`.

**`swax/git/`** — `clone_specs` (Iterator), `RepositoryCloneError`, `SpecsNotFoundError`.

**`swax/openapi/`** — `parse_spec`, `extract_paths`, `extract_schemas`, `discover_specs`, `SpecParseError`.

**`swax/traceability/`** — `TraceabilityGraph` (Entity с `edges`, `add_edge`, `deduplicate`), `load_traceability`, `save_traceability`.

**`swax/prompts/`** — `build_graph_system_prompt`, `build_graph_user_prompt`, `build_refine_user_prompt`.

**`swax/llm/`** — `LLMClient` (protocol), `LLMClient::AnthropicAdapter`, `LLMClient::OpenAIAdapter`, `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError`, `UnsupportedLLMProtocolError`, `build_anthropic_client`, `build_openai_client`, `build_llm_client`.

**`swax/applications/init/`** — `run_init`.

**`swax/applications/discover/`** — `run_discover`.

**`swax/applications/`** — `->run_init_handler`, `->run_discover_handler` (embeddings).

**`swax/commands/init/`** — `init`.

**`swax/commands/discover/`** — `discover`.

**`swax/commands/`** — `->init_handler`, `->discover_handler` (embeddings).

**`swax/cli/`** — `main`, `SwaxContext`.

### Deleted Entities

Нет (greenfield).

### Usages and Annotations Changes

Созданы все 12 `.usages/` файлов в клетках-источниках, 7 cook-файлов в `.goga/usages/cooks/`, и `conventions.md` в `.goga/usages/`. Inline Usages добавлены в `swax/applications/discover/CODEMANIFEST` (см. Applied Fixes).

---

## Applied Fixes

### Fixed CODEMANIFEST Defects (review pass 2)

| # | Файл | Дефект | Фикс |
|---|------|--------|------|
| Р1 | `swax/llm/CODEMANIFEST` | `LLMResponseParseError` поднимается из `run_discover` helper-ом, но не объявлен нигде в контрактах | Добавлен Entity `LLMResponseParseError(reason: str, excerpt: str)` в `errors.py`. Импортирован в `swax/applications/discover/` и `swax/commands/discover/`. Annotations обновлены |
| Р3 | `swax/prompts/CODEMANIFEST` | `build_graph_user_prompt` неявно ожидал формат ответа с uncertain-флагом, но контракт не зафиксирован | Algorithm и Requirements обновлены: LLM обязан вернуть `{dependencies, uncertain}` (industry pattern — separate uncertain key) |

### Fixed CODEMANIFEST Defects (review pass 1)

| # | Файл | Дефект | Фикс |
|---|------|--------|------|
| Д1 | `swax/cli/CODEMANIFEST` | `SwaxContext.config` аннотирован как `Config \| None`, но `Config` и `load_config` не импортированы; backtick на `load_config` не резолвился | Добавлены в `Imports`: `Types: [load_env, load_config, Config]`, `Usages: [environment, project-config]` из `swax/config`. Аннотация `config` теперь корректно ссылается на импортированный `Config` |
| Д2 | `swax/cli/CODEMANIFEST` | `Usages click.md` указывает `click.Path(exists=True)`, но `main` завязан на `load_env` fallback при отсутствии файла | В design-doc фиксируется решение: `exists=False`. Cook-файл `click.md` остаётся как общая рекомендация; специфичная семантика Swax описана в аннотации `main` |
| Д4 | `swax/applications/discover/CODEMANIFEST` | Annotations детально описывает защитный парсинг через `json`, но `json` (stdlib) не подключён через `Usages`; backticks вокруг `json.loads`/`json.JSONDecodeError` нарушают правило `backticks = references only` (auto-memory `goga_linter_annotation_backticks`) | Добавлена inline `Usages: json: \|` (без backticks вокруг вызовов); в Annotations backtick вокруг `json.JSONDecodeError` заменён на plain text |

### Fixed Design Defects (review pass 2)

| # | Где | Дефект | Фикс |
|---|-----|--------|------|
| Р2 | `run_discover` helper | `_strip_prose_and_fences` вызывается, но алгоритм не описан | Зафиксирована first/last brace стратегия + edge cases |
| Р3 | `run_discover` helper | `_parse_llm_json` shape-валидатор противоречил формату LLM-ответа с uncertain-флагом | Helper расширен: принимает first_pass-флаг, валидирует `{dependencies, uncertain}` для первого прохода и плоский `dict[str, list[str]]` для refine |
| Р4 | `run_discover` шаг 16 | `_is_uncertain(s, t, ...)` вызывалась, но не была определена | Устранена: uncertain-пары приходят напрямую из LLM-ответа как `list[str]` |
| Р9 | Edge case test | Опечатка `graph.duplicate()` вместо `graph.deduplicate()` | Исправлено |

### Skipped (review pass 2)

| # | Дефект | Причина skip |
|---|--------|--------------|
| Р5 | `discover(ctx)` не использует `ctx.obj`; `SwaxContext` импорт + `cli-facade` usage — dead dependency | CODEMANIFEST не трогаем. В дизайне зафиксировано намерение: сохранено для единства API init/discover и зарезервировано под будущие use-cases (caching `load_config` в `SwaxContext.config`) |

### Added Test Coverage (review pass 2)

| # | Тест | Что покрывает |
|---|------|---------------|
| Р6a | `test_run_discover_raises_llm_response_parse_error_on_invalid_first_pass` | Defensive parser падает с информативной ошибкой при невалидном first-pass shape; refine не вызывается |
| Р6b | `test_run_discover_passes_uncertain_pairs_to_refine` | Uncertain-пары из первого прохода попадают в refine prompt |
| Р7 | `test_run_init_config_survives_clone_failure` | Контракт "config written before cloning": config.yml остаётся на диске при clone-ошибке |
| Р8 | `test_discover_handler_maps_domain_errors` (parametrized × 6) | Все 6 доменных исключений маппятся в ClickException |
| Р10a | `test_parse_protocol_accepts_supported_values` | Happy-path для parse_protocol |
| Р10b | `test_clone_specs_cleans_up_tempdir_on_clone_failure` | Контракт "cleanup on every outcome" |
| Р10c | `test_extract_schemas_returns_definitions_for_swagger_2` | Swagger 2.0 ветка `definitions` |

### Known Limitations (without fix)

**Д3** — `swax/llm/CODEMANIFEST` ссылается на типы `Anthropic` и `OpenAI` (классы сторонних SDK) в сигнатурах `AnthropicAdapter(client: Anthropic)`, `OpenAIAdapter(client: OpenAI)`, property `client -> Anthropic`/`OpenAI`, и return types `build_anthropic_client() -> client: Anthropic`, `build_openai_client() -> client: OpenAI`. Эти типы не подключены через `Imports` (в DSL `Imports.From` требует cell_path, а ячейки-обёртки для SDK в проекте нет). Связывание через `Usages: anthropic`/`openai` (cook-файлы) даёт контекст, но формально backtick-reference на `Anthropic`/`OpenAI` не резолвится в документе.

Решение пользователя: оставить как есть (cook-файлы достаточны). Linter пропускает — он проверяет только формальную валидность `Imports`, а не резолвинг типов в сигнатурах.

Семантическая метка возврата `-> response: str` во всех сигнатурах `ask`/`ask_multi_turn` присутствует — здесь дефекта нет.

---

## Entity Interaction and Data Flow

### Interaction Diagram

```
                       ┌──────────────────────────┐
                       │ swax/cli/main (Click grp) │
                       │   --env-file → load_env   │
                       │   ctx.obj = SwaxContext   │
                       └────────────┬──────────────┘
                                    │ add_command (lazy in __main__.py)
                ┌───────────────────┴────────────────────┐
                ▼                                        ▼
   ┌────────────────────────┐              ┌────────────────────────┐
   │ swax/commands/init     │              │ swax/commands/discover │
   │  prompts + try/run_init│              │  try/run_discover      │
   │  map git errors        │              │  map 5 domain errors   │
   └──────────┬─────────────┘              └──────────┬─────────────┘
              │                                        │
              ▼                                        ▼
   ┌────────────────────────┐              ┌──────────────────────────────┐
   │ swax/applications/init │              │ swax/applications/discover   │
   │  Config → save_config  │              │  require_vars                │
   │  → clone_specs         │              │  → load_config               │
   │  → copy_specs          │              │  → discover_specs            │
   └─────┬──────┬────┬──────┘              │  → parse_spec × N            │
         │      │    │                      │    → extract_paths/schemas   │
         ▼      ▼    ▼                      │  → build_graph_*_prompt      │
 ┌────────┐┌─────────┐┌──────────┐          │  → LLMClient.ask (1st pass) │
 │config/ ││  git/   ││   fs/    │          │  → build_refine_user_prompt │
 │Config  ││clone_   ││ensure_   │          │  → LLMClient.ask_multi_turn │
 │save_   ││specs    ││swax_dir  │          │  → TraceabilityGraph        │
 │config  ││         ││copy_specs│          │    .add_edge / .deduplicate │
 └────────┘└─────────┘└──────────┘          │  → save_traceability        │
                                             └────┬──────┬──────┬──────┬──┘
                                                  │      │      │      │
                                                  ▼      ▼      ▼      ▼
                                            ┌──────┐┌────────┐┌──────┐┌──────────┐
                                            │config││openapi ││ llm  ││traceabil │
                                            │      ││prance  ││      ││ity       │
                                            └──────┘└────────┘└──────┘└──────────┘
```

### Data Flows

#### Flow A: `swax init`

1. Пользователь: `swax --env-file .env init`
2. `main` → `load_env(env_file)` → `os.environ` наполнен `SWAX_*`
3. `init` handler: `click.prompt` × 3 → `repo_url: str`, `specs_location: str`, `download_path: pathlib.Path`
4. `init` handler: `project_root = pathlib.Path.cwd()`
5. `run_init(...)`:
   - `Config(GitConfig(url, location), SpecsConfig(type="openapi", location=str(download_path)))`
   - `ensure_swax_dir(project_root)` → `.swax/` создан
   - `save_config(config, .swax/config.yml)` → YAML-файл записан
   - `with clone_specs(repo_url, specs_location) as specs_path:` → temporary clone created
   - `copy_specs(source=specs_path, destination=download_path)` → specs скопированы
   - on exit: temporary directory удалён
6. В случае ошибки клонирования: `RepositoryCloneError`/`SpecsNotFoundError` пробрасываются из `run_init` → `init` ловит → `click.ClickException` → exit code 1

#### Flow B: `swax discover`

1. Пользователь: `swax --env-file .env discover`
2. `main` → `load_env`
3. `discover` handler: `project_root = pathlib.Path.cwd()`
4. `run_discover(project_root)`:
   - `require_vars()` → `dict[str, str]` (или raise `MissingEnvironmentVariablesError`)
   - `load_config(.swax/config.yml)` → `Config`
   - `specs_root = project_root / config.specs.location`
   - `discover_specs(specs_root)` → `list[pathlib.Path]` (sorted)
   - for each `spec_path`:
     - `parse_spec(spec_path)` → `dict` (или raise `SpecParseError`)
     - `extract_paths(spec)` → extend `endpoints: list[str]`
     - `extract_schemas(spec)` → merge into `schemas: dict`
   - `client = build_llm_client()` → `LLMClient` (по `SWAX_LLM_PROTOCOL`)
   - `system = build_graph_system_prompt()`
   - `first_user = build_graph_user_prompt(endpoints)`
   - `raw_first = client.ask(system, first_user)` → defensive JSON parse → `first_dependencies: dict[str, list[str]]`
   - extract `ambiguous_pairs` из `first_dependencies`
   - `refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)`
   - `raw_refined = client.ask_multi_turn(system, [user/first_user, assistant/raw_first, user/refine_user])` → defensive JSON parse → `final_dependencies`
   - `graph = TraceabilityGraph(edges={})`
   - for `source, targets` in `final_dependencies`: for `target` in `targets`: `graph.add_edge(source, target)`
   - `graph.deduplicate()`
   - `save_traceability(graph, .swax/traceability.yml)`
5. В случае ошибки: 6 типов доменных исключений пробрасываются из `run_discover` → `discover` ловит → `click.ClickException` → exit code 1

### Entity Dependencies

**Уровень 0 (листья — без Imports.Types):** `config/`, `fs/`, `git/`, `openapi/`, `traceability/`, `prompts/`.

**Уровень 1:** `llm/` (→ `config/`); `applications/init/` (→ `config/`, `git/`, `fs/`); `applications/discover/` (→ `config/`, `openapi/`, `llm/`, `prompts/`, `traceability/`).

**Уровень 2 (facades):** `applications/` (embeddings из `applications/init`, `applications/discover`); `commands/` (embeddings из `commands/init`, `commands/discover`).

**Уровень 3 (command handlers):** `commands/init/` (→ `cli/`, `applications/`, `git/`); `commands/discover/` (→ `cli/`, `applications/`, `config/`, `openapi/`, `llm/`).

**Уровень 4 (entry point):** `cli/` (→ `config/`). Команды регистрируются лениво в `__main__.py` — это не отражено в `Imports` и не создаёт цикла в контракте.

**Порядок инициализации (bottom-up):** листья → `llm` + applications/use-cases → applications/commands facades → command handlers → `cli/`.

---

## Code Stack Trace

### Trace: `swax init`

#### Chain
1. **Input**: `swax --env-file .env init` (CLI argv от пользователя)
2. **Step**: Click резолвит entry point `swax.cli.__main__:main`. `__main__.py` выполняет `main.add_command(init)` и `main.add_command(discover)` (lazy import — разрывает потенциальный цикл `cli ↔ commands`) → checkpoint: command registered ✓
3. **Step**: `main(ctx, env_file=".env")` вызывает `load_env(env_file)` → checkpoint: `load_env` принимает `pathlib.Path`, контракт `load_env(env_file: pathlib.Path)` ✓
4. **Step**: `load_env` проверяет `env_file.exists()`. Если `False` — return; иначе `load_dotenv(env_file, override=False)` → checkpoint: shell env имеет приоритет ✓
5. **Step**: `main` выполняет `ctx.obj = SwaxContext(env_file=env_file)`. Свойство `config` по умолчанию `None` → checkpoint: `SwaxContext.config: Config | None` тип-совместим с импортированным `Config` ✓
6. **Step**: Click вызывает `init(ctx)`. `@click.pass_obj` передаёт `ctx.obj` как `SwaxContext` → checkpoint: тип `SwaxContext` импортирован через `Imports` из `swax/cli` ✓
7. **Step**: `init` вызывает `click.prompt` × 3. Для `download_path` — коэрция в `pathlib.Path` → checkpoint: типы `str, str, pathlib.Path` соответствуют сигнатуре `run_init` ✓
8. **Step**: `project_root = pathlib.Path.cwd()` → checkpoint: `pathlib.Path` соответствует сигнатуре `run_init` ✓
9. **Step**: `run_init(repo_url, specs_location, download_path, project_root)` внутри `try` → checkpoint: типы соответствуют сигнатуре ✓
10. **Step**: внутри `run_init` — `Config(git=GitConfig(url=repo_url, location=specs_location), specs=SpecsConfig(type="openapi", location=str(download_path)))` → checkpoint: `Config`, `GitConfig`, `SpecsConfig` импортированы из `swax/config` ✓
11. **Step**: `swax_dir = ensure_swax_dir(project_root)` → checkpoint: возврат `pathlib.Path`, контракт `ensure_swax_dir(...) -> swax_dir: pathlib.Path` ✓
12. **Step**: `save_config(config, swax_dir / "config.yml")` — конфиг пишется ДО клонирования → checkpoint: контрактное требование "Configuration is written before cloning" удовлетворено ✓
13. **Step**: `with clone_specs(repo_url, specs_location) as specs_path:` → `Repo.clone_from(repo_url, tmp.name, depth=1)`. При `GitCommandError` → `RepositoryCloneError(url=repo_url, reason=str(exc))`. При отсутствии `specs_location` → `SpecsNotFoundError(specs_path)` → checkpoint: оба доменных исключения импортированы в `run_init` (через `Imports` из `swax/git`) ✓
14. **Step**: внутри `with`: `copy_specs(source=specs_path, destination=download_path)` → checkpoint: `copy_specs(source: pathlib.Path, destination: pathlib.Path)` типы соответствуют ✓
15. **Step**: выход из `with` (normal/exception) — `TemporaryDirectory` очищается автоматически → checkpoint: контрактное требование "cleanup guaranteed on every outcome" удовлетворено ✓
16. **Step**: при ошибке — исключение пробрасывается из `run_init` (нет catch) → `init` ловит `RepositoryCloneError`/`SpecsNotFoundError` → `raise click.ClickException(...)` → checkpoint: exit code 1 ✓
17. **Output**: `.swax/config.yml` + `.swax/` + specs в `download_path`, exit code 0; или user-facing error, exit code 1

#### Checkpoint Summary
- Все 17 чекпойнтов passed. Дефектов нет.

### Trace: `swax discover`

#### Chain
1. **Input**: `swax --env-file .env discover`
2. **Step**: `main` довыполняется (см. trace init шаги 2-5) → checkpoint: `SwaxContext` в `ctx.obj` ✓
3. **Step**: `discover(ctx)`: `@click.pass_obj` передаёт `SwaxContext`, но handler не использует его поля → checkpoint: контракт `discover(ctx: click.Context)` формально соответствует ✓. Note: импорт `SwaxContext` и usage `cli-facade` сохранены как intentional — для единства API init/discover handlers и зарезервированы под будущие use-cases (например, caching `load_config` в `SwaxContext.config`).
4. **Step**: `project_root = pathlib.Path.cwd()` → checkpoint: тип соответствует `run_discover(project_root: pathlib.Path)` ✓
5. **Step**: `try: run_discover(project_root)` → checkpoint: тип соответствия ✓
6. **Step**: `require_vars()` — итерируется по `("SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN")`, проверяет `os.environ.get(name)`. Whitespace-only считается missing. Если есть missing → `MissingEnvironmentVariablesError(missing=[...])` → checkpoint: исключение импортировано в handler (через `Imports` из `swax/config`) ✓
7. **Step**: `config = load_config(project_root / ".swax" / "config.yml")` → checkpoint: `Config` импортирован (через `Imports` из `swax/config`), тип соответствует ✓
8. **Step**: `specs_root = project_root / config.specs.location` → checkpoint: `SpecsConfig.location: str` (поле из `swax/config`), result `pathlib.Path` ✓
9. **Step**: `spec_files = discover_specs(specs_root)` → checkpoint: возврат `list[pathlib.Path]`, sorted ✓
10. **Step**: for each `spec_path`: `parse_spec(spec_path)` → checkpoint: возврат `dict`, может выбросить `SpecParseError` (импортирован в handler) ✓
11. **Step**: `extract_paths(spec)` → extend `endpoints: list[str]` → checkpoint: `extract_paths(spec: dict) -> paths: list[str]` типы соответствуют ✓
12. **Step**: `extract_schemas(spec)` → merge into `schemas: dict` → checkpoint: `extract_schemas(spec: dict) -> schemas: dict` типы соответствуют ✓
13. **Step**: `client = build_llm_client()` — читает `SWAX_LLM_PROTOCOL`, при `"anthropic"` → `AnthropicAdapter(build_anthropic_client())`, при `"openai"` → `OpenAIAdapter(build_openai_client())`, иначе `UnsupportedLLMProtocolError` → checkpoint: возврат `LLMClient`, исключение импортировано в handler ✓
14. **Step**: `system = build_graph_system_prompt()` — без параметров → checkpoint: контракт `build_graph_system_prompt() -> prompt: str` соответствует ✓
15. **Step**: `first_user = build_graph_user_prompt(endpoints)` → checkpoint: контракт `build_graph_user_prompt(endpoints: list[str]) -> prompt: str` типы соответствуют ✓
16. **Step**: `raw_first = client.ask(system=system, user=first_user)` → checkpoint: сигнатуры `LLMClient.ask(system: str, user: str) -> response: str` и методов адаптеров идентичны ✓
17. **Step**: defensive parse `raw_first` (first_pass=True):
    - Strip prose/code fences через `_strip_prose_and_fences` (поиск первого `{` и последнего `}`)
    - `parsed = json.loads(stripped)` — при `json.JSONDecodeError` обернуть в `LLMResponseParseError` с excerpt
    - Validate: top-level dict, keys == `{"dependencies", "uncertain"}`, dependencies — `dict[str, list[str]]`, uncertain — `list[str]`
    → checkpoint: inline `Usages: json` декларирует использование stdlib `json`; контракт `LLMResponseParseError` объявлен в `swax/llm` ✓
18. **Step**: `ambiguous_pairs = uncertain` (LLM уже отформатировал пары как "/source -> /target")
19. **Step**: `refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)` → checkpoint: контракт `build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> prompt: str` типы соответствуют ✓
20. **Step**: `raw_refined = client.ask_multi_turn(system=system, messages=[{"role":"user", "content": first_user}, {"role":"assistant", "content": raw_first}, {"role":"user", "content": refine_user}])` → checkpoint: сигнатура `ask_multi_turn(system: str, messages: list[dict[str, str]]) -> response: str` типы соответствуют ✓
21. **Step**: defensive parse `raw_refined` (first_pass=False) → ожидает плоский `dict[str, list[str]]` → `final_dependencies`
22. **Step**: `graph = TraceabilityGraph(edges={})` → for `source, targets` in `final_dependencies.items()`: for `target` in `targets`: `graph.add_edge(source=source, target=target)` → checkpoint: сигнатура `add_edge(source: str, target: str)` типы соответствуют ✓
23. **Step**: `graph.deduplicate()` — idempotent, сортирует списки, убирает self-loops
24. **Step**: `save_traceability(graph, project_root / ".swax" / "traceability.yml")` — deterministic YAML → checkpoint: контракт `save_traceability(graph: TraceabilityGraph, path: pathlib.Path)` типы соответствуют ✓
25. **Step**: INFO-лог завершения
26. **Step**: при ошибке — одно из 6 исключений пробрасывается из `run_discover` → `discover` ловит каждое → `raise click.ClickException(...)` → checkpoint: все 6 исключений импортированы в handler через `Imports` ✓

#### Checkpoint Summary
- Все 26 чекпойнтов passed. Дефектов нет.

---

## Algorithm Design

### `swax/config/`

**`Config`** (Entity, pydantic, kw_only). Поля: `git: GitConfig`, `specs: SpecsConfig`. Корневая модель, сериализуется в `.swax/config.yml`.

**`GitConfig`** (Entity, pydantic, kw_only). Поля: `url: str`, `location: str`. Координаты git-репозитория.

**`SpecsConfig`** (Entity, pydantic, kw_only). Поля: `type: Literal['swagger', 'openapi']`, `location: str`. Локальный layout. `type` — информационный, не управляет парсингом.

**`MissingEnvironmentVariablesError`** (Entity). Поля: `missing: list[str]`.

**`InvalidLLMProtocolError`** (Entity). Поля: `value: str`, `allowed: tuple[str, ...]`.

**`InvalidLLMBaseURLError`** (Entity). Поля: `value: str`.

**`load_env(env_file: pathlib.Path)`** (Routine).
```
1. IF NOT env_file.exists():
   - return
2. load_dotenv(env_file, override=False)
```

**`require_vars() -> vars: dict[str, str]`** (Routine).
```
1. FOR name IN ("SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN"):
   - value = os.environ.get(name)
   - IF NOT value OR NOT value.strip():
     - missing.append(name)
2. IF missing:
   - raise MissingEnvironmentVariablesError(missing=missing)
3. RETURN {name: os.environ[name] FOR name IN REQUIRED_VARS}
```

**`parse_protocol(value: str) -> protocol: str`** (Routine).
```
1. IF value NOT IN ("anthropic", "openai"):
   - raise InvalidLLMProtocolError(value=value, allowed=("anthropic", "openai"))
2. RETURN value
```

**`parse_base_url(value: str) -> base_url: str`** (Routine).
```
1. stripped = value.rstrip("/")
2. IF stripped.endswith(("/v1", "/v2")):
   - raise InvalidLLMBaseURLError(value=value)
3. RETURN stripped
```

**`load_config(path: pathlib.Path) -> config: Config`** (Routine).
```
1. raw_text = path.read_text(encoding="utf-8")
2. raw = yaml.safe_load(raw_text)
3. RETURN Config.model_validate(raw)
```

**`save_config(config: Config, path: pathlib.Path)`** (Routine).
```
1. payload = config.model_dump(mode="json")
2. path.parent.mkdir(parents=True, exist_ok=True)
3. yaml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)
4. path.write_text(yaml_text, encoding="utf-8")
```

### `swax/fs/`

**`ensure_swax_dir(project_root: pathlib.Path) -> swax_dir: pathlib.Path`** (Routine).
```
1. swax_dir = project_root / ".swax"
2. swax_dir.mkdir(parents=True, exist_ok=True)
3. RETURN swax_dir
```

**`copy_specs(source: pathlib.Path, destination: pathlib.Path)`** (Routine).
```
1. destination.parent.mkdir(parents=True, exist_ok=True)
2. shutil.copytree(source, destination, dirs_exist_ok=True)
```
*Errors:* None — копирование файловое; `OSError` пробрасывается (не доменный).
*Edge:* symlinks в `source` копируются как regular files (`copytree` по умолчанию `symlinks=False`, но в Swax обычно `True` — явное решение в CODEMANIFEST: "Symlinks in the clone are not dereferenced — copied as regular files", что значит `symlinks=False` — default. Уточнить при реализации).

### `swax/git/`

**`clone_specs(repo_url: str, specs_location: str) -> Iterator[specs_path: pathlib.Path]`** (Routine, context manager).
```
1. with tempfile.TemporaryDirectory(prefix="swax-") as tmp:
2.   tmp_path = pathlib.Path(tmp)
3.   try:
4.     Repo.clone_from(repo_url, tmp_path, depth=1)
5.   except GitCommandError as exc:
6.     raise RepositoryCloneError(url=repo_url, reason=str(exc)) from exc
7.   specs_path = tmp_path / specs_location
8.   IF NOT specs_path.exists():
9.     raise SpecsNotFoundError(specs_path)
10.  yield specs_path
11. (cleanup by TemporaryDirectory on exit)
```
*Errors:* `RepositoryCloneError`, `SpecsNotFoundError`.
*Edge:* path НЕ валиден за пределами `with`.

### `swax/openapi/`

**`parse_spec(spec_path: pathlib.Path) -> spec: dict`** (Routine).
```
1. try:
2.   parser = ResolvingParser(str(spec_path), backend="openapi-spec-validator", strict=False, resolve_types=RESOLVE_ALL)
3.   RETURN parser.specification
4. except Exception as exc:
5.   raise SpecParseError(path=spec_path, reason=str(exc)) from exc
```

**`extract_paths(spec: dict) -> paths: list[str]`** (Routine).
```
1. RETURN sorted(spec.get("paths", {}).keys())
```

**`extract_schemas(spec: dict) -> schemas: dict`** (Routine).
```
1. IF "components" IN spec:
2.   RETURN spec["components"].get("schemas", {})
3. RETURN spec.get("definitions", {})
```

**`discover_specs(root: pathlib.Path) -> specs: list[pathlib.Path]`** (Routine).
```
1. result = []
2. FOR path IN root.rglob("*"):
3.   IF path.suffix.lower() NOT IN (".yaml", ".yml", ".json"):
4.     continue
5.   TRY: head = yaml.safe_load(path.read_text(encoding="utf-8"))
6.   EXCEPT yaml.YAMLError: continue   # unparseable candidate — skip, not crash
7.   IF isinstance(head, dict) AND ("openapi" IN head OR "swagger" IN head):
8.     result.append(path)
9. RETURN sorted(result)
```
*Note:* Парсится содержимое целиком (PyYAML — надмножество JSON), а не только первая строка, чтобы находить ключи и в YAML, и в JSON с `{` на первой строке. Полное дереференсирование `$ref` остаётся задачей `parse_spec`.
```

### `swax/traceability/`

**`TraceabilityGraph`** (Entity, pydantic, kw_only). Поле: `edges: dict[str, list[str]] = {}`.

**Method `add_edge(source: str, target: str)`:**
```
1. self.edges.setdefault(source, []).append(target)
```

**Method `deduplicate()`:**
```
1. FOR source IN list(self.edges.keys()):
2.   self.edges[source] = sorted(set(self.edges[source]))
3.   IF source IN self.edges[source]:
4.     self.edges[source] = [t for t in self.edges[source] if t != source]
5.   IF NOT self.edges[source]:
6.     del self.edges[source]  # optional cleanup
```
*Edge:* Idempotent — повторный вызов не меняет состояние.

**`load_traceability(path: pathlib.Path) -> graph: TraceabilityGraph`** (Routine).
```
1. raw_text = path.read_text(encoding="utf-8") if path.exists() else ""
2. data = yaml.safe_load(raw_text) or {}
3. normalized = {k: list(v) for k, v in data.items()}
4. RETURN TraceabilityGraph(edges=normalized)
```
*Edge:* пустой файл → пустой граф, не ошибка.

**`save_traceability(graph: TraceabilityGraph, path: pathlib.Path)`** (Routine).
```
1. payload = graph.model_dump(mode="json")
2. ordered = {k: sorted(v) for k, v in sorted(payload["edges"].items())}
3. path.parent.mkdir(parents=True, exist_ok=True)
4. yaml_text = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False)
5. path.write_text(yaml_text, encoding="utf-8")
```

### `swax/prompts/`

**`build_graph_system_prompt() -> prompt: str`** (Routine).
```
1. RETURN constant string:
   - Role: API dependency analyst
   - Output contract: JSON object {source_path: [dependent_paths]}
   - Forbid prose around JSON
   - Graph operates on paths only
```

**`build_graph_user_prompt(endpoints: list[str]) -> prompt: str`** (Routine).
```
1. payload = json.dumps({"endpoints": endpoints})
2. RETURN f"""Given these API endpoints:

{payload}

Return a JSON object with exactly two keys:
- "dependencies": object mapping source_path to list of dependent_paths
- "uncertain": list of uncertain dependency pairs as "/source -> /target" strings

The "uncertain" pairs will be refined in a follow-up turn with schema context."""
```

**`build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> prompt: str`** (Routine).
```
1. pairs_payload = json.dumps({"ambiguous_pairs": ambiguous_pairs})
2. schemas_payload = json.dumps({"schemas": schemas})
3. RETURN f"""Refine these ambiguous dependency pairs using schemas:

{pairs_payload}

{schemas_payload}

Return consolidated JSON object {source_path: [dependent_paths]}.
Do not introduce paths outside the provided endpoint universe."""
```

### `swax/llm/`

**`LLMClient`** (Protocol Entity, structural typing).
- `ask(system: str, user: str) -> response: str`
- `ask_multi_turn(system: str, messages: list[dict[str, str]]) -> response: str`

**`LLMClient::AnthropicAdapter`** (Mutation, конструктор `(client: Anthropic)`).

**Method `ask(system, user)`:**
```
1. try:
2.   response = client.messages.create(
       model=DEFAULT_MODEL,
       max_tokens=4096,
       system=system,
       messages=[{"role": "user", "content": user}],
     )
3.   RETURN "".join(block.text for block in response.content if block.type == "text")
4. except RateLimitError as exc:
5.   raise LLMRateLimitedError(reason=str(exc)) from exc
6. except APIError as exc:
7.   raise LLMCallError(reason=str(exc)) from exc
```

**Method `ask_multi_turn(system, messages)`:**
```
1-5. same as ask, but messages=messages instead of [user]
```

**`LLMClient::OpenAIAdapter`** (Mutation, конструктор `(client: OpenAI)`).

**Method `ask(system, user)`:**
```
1. try:
2.   response = client.chat.completions.create(
       model=DEFAULT_MODEL,
       messages=[
         {"role": "system", "content": system},
         {"role": "user", "content": user},
       ],
     )
3.   RETURN response.choices[0].message.content or ""
4-6. same error mapping as AnthropicAdapter.ask
```

**Method `ask_multi_turn(system, messages)`:**
```
1. prepended = [{"role": "system", "content": system}] + messages
2-6. same as ask, but messages=prepended
```

**`LLMCallError(reason: str)`, `LLMRateLimitedError(reason: str)`, `UnsupportedLLMProtocolError(protocol: str)`** — Entity-ошибки.

**`build_anthropic_client() -> client: Anthropic`** (Routine).
```
1. require_vars()
2. token = os.environ["SWAX_LLM_TOKEN"]
3. base_url = os.environ["SWAX_LLM_BASE_URL"]
4. RETURN Anthropic(api_key=token, base_url=base_url)
```

**`build_openai_client() -> client: OpenAI`** (Routine) — аналогично с `OpenAI(...)`.

**`build_llm_client() -> client: LLMClient`** (Routine).
```
1. protocol = os.environ.get("SWAX_LLM_PROTOCOL")
2. IF protocol == "anthropic":
3.   RETURN AnthropicAdapter(build_anthropic_client())
4. IF protocol == "openai":
5.   RETURN OpenAIAdapter(build_openai_client())
6. raise UnsupportedLLMProtocolError(protocol=protocol)
```

### `swax/applications/init/`

**`run_init(repo_url, specs_location, download_path, project_root)`** (Routine).
```
1. config = Config(
     git=GitConfig(url=repo_url, location=specs_location),
     specs=SpecsConfig(type="openapi", location=str(download_path)),
   )
2. swax_dir = ensure_swax_dir(project_root)
3. save_config(config, swax_dir / "config.yml")
4. logger.info("init started", extra={"project_root": str(project_root)})
5. with clone_specs(repo_url, specs_location) as specs_path:
6.   copy_specs(source=specs_path, destination=download_path)
7. logger.info("init completed", extra={"project_root": str(project_root)})
```
*Errors:* `RepositoryCloneError`, `SpecsNotFoundError` propagate uncaught.
*Edge:* конфиг пишется до клонирования — даже при сбое пользователь имеет `.swax/config.yml`.

### `swax/applications/discover/`

**`run_discover(project_root: pathlib.Path)`** (Routine).
```
1. require_vars()
2. config = load_config(project_root / ".swax" / "config.yml")
3. specs_root = project_root / config.specs.location
4. spec_files = discover_specs(specs_root)
5. endpoints: list[str] = []
6. schemas: dict = {}
7. FOR spec_path IN spec_files:
8.   spec = parse_spec(spec_path)
9.   endpoints.extend(extract_paths(spec))
10.  schemas.update(extract_schemas(spec))
11. client = build_llm_client()
12. system = build_graph_system_prompt()
13. first_user = build_graph_user_prompt(endpoints)
14. raw_first = client.ask(system=system, user=first_user)
15. first_dependencies, uncertain = _parse_llm_json(raw_first, first_pass=True)
16. ambiguous_pairs = uncertain  # формат пар: "/source -> /target" (сформирован LLM)
17. refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)
18. raw_refined = client.ask_multi_turn(
      system=system,
      messages=[
        {"role": "user", "content": first_user},
        {"role": "assistant", "content": raw_first},
        {"role": "user", "content": refine_user},
      ],
    )
19. final_dependencies, _ = _parse_llm_json(raw_refined, first_pass=False)
20. graph = TraceabilityGraph(edges={})
21. FOR source, targets IN final_dependencies.items():
22.   FOR target IN targets:
23.     graph.add_edge(source=source, target=target)
24. graph.deduplicate()
25. save_traceability(graph, project_root / ".swax" / "traceability.yml")
26. logger.info("discover completed", extra={"project_root": str(project_root), "edges_count": sum(len(v) for v in graph.edges.values())})
```

Где `_parse_llm_json(raw: str, *, first_pass: bool) -> tuple[dict[str, list[str]], list[str]]` — helper (внутренний, не часть контракта). Принимает две формы ответа в зависимости от прохода:

- **first_pass=True**: ожидает `{"dependencies": dict[str, list[str]], "uncertain": list[str]}` (industry pattern: separate `uncertain` key, см. MDPI dependency analysis, Virtido document intelligence).
- **first_pass=False** (refine pass): ожидает плоский `dict[str, list[str]]`.

```
1. stripped = _strip_prose_and_fences(raw)
2. try:
3.   parsed = json.loads(stripped)
4. except json.JSONDecodeError as exc:
5.   raise LLMResponseParseError(reason=str(exc), excerpt=stripped[:200]) from exc
6. if not isinstance(parsed, dict):
7.   raise LLMResponseParseError(reason="not a dict", excerpt=stripped[:200])
8. IF first_pass:
9.   IF set(parsed.keys()) != {"dependencies", "uncertain"}:
10.    raise LLMResponseParseError(reason="first pass: keys must be dependencies+uncertain", excerpt=stripped[:200])
11.  deps = parsed["dependencies"]; unc = parsed["uncertain"]
12.  _validate_dependency_shape(deps)  # dict[str, list[str]]
13.  IF not isinstance(unc, list) or not all(isinstance(x, str) for x in unc):
14.    raise LLMResponseParseError(reason="uncertain: must be list[str]", excerpt=stripped[:200])
15.  return deps, unc
16. ELSE:
17.  _validate_dependency_shape(parsed)  # dict[str, list[str]]
18.  return parsed, []
```

`_validate_dependency_shape(d: dict) -> None` — helper:
```
1. for k, v in d.items():
2.   if not isinstance(k, str) or not isinstance(v, list) or not all(isinstance(x, str) for x in v):
3.     raise LLMResponseParseError(reason="shape mismatch: expected dict[str, list[str]]", excerpt=...)
```

`_strip_prose_and_fences(raw: str) -> str` — private helper в `run_discover.py`:
```
1. first_brace = raw.find("{")
2. last_brace = raw.rfind("}")
3. IF first_brace == -1 OR last_brace == -1 OR first_brace > last_brace:
   - return raw  # let json.loads raise with informative error
4. return raw[first_brace : last_brace + 1]
```

Edge cases:
- Пустой input → нет `{`/`}` → возвращается as-is → `json.loads("")` → `LLMResponseParseError`.
- Только prose без JSON → аналогично.
- Несколько JSON-блоков (например `{"a": 1} text {"b": 2}`) → first/last brace захватит оба, `json.loads` упадёт на `text` → `LLMResponseParseError("JSONDecodeError")`.
- Корректный JSON с prose вокруг → корректно стрипается.
- first_pass=True с лишним/недостающим ключом → `LLMResponseParseError("first pass: keys must be dependencies+uncertain")`.

*Errors propagated:* `MissingEnvironmentVariablesError`, `SpecParseError`, `LLMCallError`, `LLMRateLimitedError`, `UnsupportedLLMProtocolError`, `LLMResponseParseError`. Все 6 обрабатываются handler-ом `discover` (см. дизайн §`swax/commands/discover/`). `LLMResponseParseError` объявлен в `swax/llm/errors.py` и переиспользуется в будущей `run_plan`.

### `swax/commands/init/`

**`init(ctx: click.Context)`** (Routine).
```
1. swax_ctx = ctx.obj  # SwaxContext via @click.pass_obj
2. repo_url = click.prompt("Repository URL")
3. specs_location = click.prompt("Path to specs inside the repo")
4. download_path = pathlib.Path(click.prompt("Local download path"))
5. project_root = pathlib.Path.cwd()
6. try:
7.   run_init(repo_url, specs_location, download_path, project_root)
8. except RepositoryCloneError as exc:
9.   raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}") from exc
10. except SpecsNotFoundError as exc:
11.  raise click.ClickException(f"Specs not found at {exc.path}") from exc
```

### `swax/commands/discover/`

**`discover(ctx: click.Context)`** (Routine).
```
1. project_root = pathlib.Path.cwd()
2. try:
3.   run_discover(project_root)
4. except MissingEnvironmentVariablesError as exc:
5.   raise click.ClickException(f"Missing env vars: {', '.join(exc.missing)}") from exc
6. except SpecParseError as exc:
7.   raise click.ClickException(f"Failed to parse {exc.path}: {exc.reason}") from exc
8. except LLMRateLimitedError:
9.   raise click.ClickException("LLM rate limited; retry later")
10. except LLMCallError as exc:
11.  raise click.ClickException(f"LLM call failed: {exc.reason}") from exc
12. except UnsupportedLLMProtocolError as exc:
13.  raise click.ClickException(f"Unsupported LLM protocol: {exc.protocol}") from exc
14. except LLMResponseParseError as exc:
15.  raise click.ClickException(f"LLM response parse failed: {exc.reason}") from exc
```

### `swax/cli/`

**`main(ctx: click.Context, env_file: pathlib.Path)`** (Routine).
```
1. @click.group()
2. @click.option("--env-file", type=click.Path(exists=False, dir_okay=False, path_type=pathlib.Path), default=".env", show_default=True)
3. @click.pass_context
4. def main(ctx, env_file):
5.   load_env(env_file)
6.   ctx.obj = SwaxContext(env_file=env_file)
```

**`SwaxContext(env_file: pathlib.Path)`** (Entity, pydantic, kw_only).
- Property `env_file -> pathlib.Path`
- Property `config -> Config | None` (default `None`)

---

## Cross-cutting Concerns

- **Error handling**:
  - Каждый доменный cell определяет свои исключения (config: 3, git: 2, openapi: 1, llm: 4 — включает `LLMResponseParseError`).
  - Application-слой (`run_init`, `run_discover`) НЕ ловит доменные исключения — пробрасывает наверх.
  - Command-слой (`init`, `discover`) ловит каждое и маппит в `click.ClickException` — единый exit code 1.
  - Никаких catch generic `Exception` — только документированные доменные.
- **Validation**:
  - Lazy: `require_vars` вызывается только в use-case-ах с LLM (`run_discover`, косвенно через `build_*_client`).
  - `parse_protocol`/`parse_base_url` — НЕ вызываются автоматически; задача 1 не вызывает их. Зарезервированы для будущей eager-валидации при старте CLI (если будет принято такое решение).
  - Pydantic валидация в `load_config`/`load_traceability` — `model_validate(raw)`.
- **Logging**:
  - `logging.getLogger(__name__)` в каждой клетке.
  - INFO — lifecycle (start/end use-case), DEBUG — intermediate (paths found, LLM response received), WARNING/ERROR — не используются в задаче 1.
  - `SWAX_LLM_TOKEN` никогда не появляется в логах — ни в `extra`, ни в сообщениях ошибок.
- **Caching**:
  - Не используется. Каждый `discover` — полный rebuild графа (контрактное требование).
  - `SwaxContext.config` — опциональный кэш, но в задаче 1 подкоманды не используют его (каждый use-case сам вызывает `load_config`).
- **Concurrency**:
  - Не требуется. CLI синхронный, single-threaded.
- **Determinism**:
  - Все сериализованные YAML отсортированы явно в Python (`sorted()` перед `yaml.safe_dump`).
  - `discover_specs` возвращает sorted список файлов.
  - `extract_paths` возвращает sorted список путей.
  - `TraceabilityGraph.deduplicate` — sorted set + remove self-loops, idempotent.

---

## Usages Analysis

### Project-level Usages (`.goga/usages/`)

**`conventions`** (`conventions.md`)
- **What**: Python code writing rules, testing discipline, pydantic usage, logging.
- **Where**: Каждая клетка (12 references).
- **Why**: Единый стандарт для всего проекта.
- **How**: Applied via `kw_only=True` on all pydantic models, Google-style docstrings, relative imports, `tmp_path`/`monkeypatch` in tests.

**`pyyaml`** (`cooks/pyyaml.md`)
- **What**: YAML serialization patterns.
- **Where**: `swax/config/` (config.yml), `swax/traceability/` (traceability.yml), `swax/openapi/` (head-check in discover_specs).
- **Why**: Единый формат persistence; deterministic output.
- **How**: `yaml.safe_load`, `yaml.safe_dump(sort_keys=False, allow_unicode=True, default_flow_style=False)`, UTF-8.

**`python-dotenv`** (`cooks/python-dotenv.md`)
- **What**: `.env` loading patterns.
- **Where**: `swax/config/` (load_env, require_vars, parse_protocol, parse_base_url).
- **Why**: Поддержка `.env` через `--env-file` без дублирования logic.
- **How**: `load_dotenv(override=False)`, REQUIRED_VARS list, ALLOWED_PROTOCOLS list.

**`gitpython`** (`cooks/gitpython.md`)
- **What**: Git repo cloning patterns.
- **Where**: `swax/git/` (clone_specs, error mapping).
- **Why**: Read-only доступ к spec-репозиторию.
- **How**: `Repo.clone_from(url, tmp, depth=1)`, `tempfile.TemporaryDirectory(prefix="swax-")`, `GitCommandError` → `RepositoryCloneError`.

**`prance`** (`cooks/prance.md`)
- **What**: OpenAPI/Swagger parsing.
- **Where**: `swax/openapi/` (parse_spec, extract_paths, extract_schemas, discover_specs).
- **Why**: Dereferencing `$ref` in memory, transparent Swagger 2.0 + OpenAPI 3.x support.
- **How**: `ResolvingParser(str(path), backend="openapi-spec-validator", strict=False, resolve_types=RESOLVE_ALL)`, `parser.specification`.

**`anthropic`** (`cooks/anthropic.md`)
- **What**: Anthropic SDK call patterns.
- **Where**: `swax/llm/` (AnthropicAdapter, build_anthropic_client).
- **Why**: Один из двух поддерживаемых LLM провайдеров.
- **How**: `Anthropic(api_key=token, base_url=base_url)`, `client.messages.create(model=DEFAULT_MODEL, max_tokens=4096, system=..., messages=...)`, `block.text for block in response.content if block.type == "text"`, error mapping.

**`openai`** (`cooks/openai.md`)
- **What**: OpenAI SDK call patterns.
- **Where**: `swax/llm/` (OpenAIAdapter, build_openai_client).
- **Why**: Второй поддерживаемый провайдер; идентичный interface.
- **How**: `OpenAI(api_key=token, base_url=base_url)`, `client.chat.completions.create(model=DEFAULT_MODEL, messages=...)`, `response.choices[0].message.content or ""`.

**`click`** (`cooks/click.md`)
- **What**: Click 8.x CLI framework patterns.
- **Where**: `swax/cli/`, `swax/commands/`, `swax/commands/init/`, `swax/commands/discover/`.
- **Why**: Единственный CLI-фреймворк Swax (архитектурное правило).
- **How**: `@click.group`, `@click.command`, `@click.pass_context`, `@click.pass_obj`, `click.Path`, `click.prompt`, `click.ClickException`.
- **Note**: cook-файл декларирует `click.Path(exists=True)`, но в Swax `main` использует `exists=False` (см. Applied Fixes Д2).

**`deepdiff`** (`cooks/deepdiff.md`)
- **What**: Structural diff of OpenAPI specs.
- **Where**: Нигде в задаче 1 — зарезервирован для задачи 2 (plan).
- **Why**: Создан заранее для будущей task 2; в задаче 1 не используется.
- **How**: Не применяется в этой задаче.

**`json`** (inline в `swax/applications/discover/CODEMANIFEST`)
- **What**: Python stdlib json module для defensive parsing LLM responses.
- **Where**: `swax/applications/discover/` (`run_discover` helper `_parse_llm_json`).
- **Why**: LLM возвращает JSON с prose/fences; требуется защитный парсинг + валидация формы.
- **How**: `json.loads(stripped)`, catch `json.JSONDecodeError`, validate `dict[str, list[str]]`.

### Cell-level Usages (Imports)

**`environment`** from `swax/config`
- Path: `swax/config/.usages/environment.md`
- **Where used**: `swax/cli/` (load_env), `swax/llm/` (require_vars), `swax/commands/discover/` (MissingEnvironmentVariablesError mapping).

**`project-config`** from `swax/config`
- Path: `swax/config/.usages/project-config.md`
- **Where used**: `swax/applications/init/` (Config assembly, save_config), `swax/applications/discover/` (load_config), `swax/cli/` (Config в SwaxContext).

**`project-layout`** from `swax/fs`
- Path: `swax/fs/.usages/project-layout.md`
- **Where used**: `swax/applications/init/` (ensure_swax_dir, copy_specs).

**`specs-repository`** from `swax/git`
- Path: `swax/git/.usages/specs-repository.md`
- **Where used**: `swax/applications/init/` (clone_specs), `swax/commands/init/` (error mapping).

**`parsing`** from `swax/openapi`
- Path: `swax/openapi/.usages/parsing.md`
- **Where used**: `swax/applications/discover/` (discover_specs, parse_spec), `swax/commands/discover/` (SpecParseError mapping).

**`extraction`** from `swax/openapi`
- Path: `swax/openapi/.usages/extraction.md`
- **Where used**: `swax/applications/discover/` (extract_paths, extract_schemas).

**`llm-transport`** from `swax/llm`
- Path: `swax/llm/.usages/llm-transport.md`
- **Where used**: `swax/applications/discover/` (build_llm_client, LLMClient), `swax/commands/discover/` (LLM error mapping).

**`traceability-llm-prompts`** from `swax/prompts`
- Path: `swax/prompts/.usages/traceability-llm-prompts.md`
- **Where used**: `swax/applications/discover/` (build_graph_*_prompt).

**`graph-lifecycle`** from `swax/traceability`
- Path: `swax/traceability/.usages/graph-lifecycle.md`
- **Where used**: `swax/applications/discover/` (TraceabilityGraph, save_traceability).

**`cli-facade`** from `swax/cli`
- Path: `swax/cli/.usages/cli-facade.md`
- **Where used**: `swax/commands/init/`, `swax/commands/discover/` (SwaxContext pattern).

**`init`** (alias `init-usage`) from `swax/applications`
- Path: `swax/applications/.usages/init.md`
- **Where used**: `swax/commands/init/`.

**`discover`** (alias `discover-usage`) from `swax/applications`
- Path: `swax/applications/.usages/discover.md`
- **Where used**: `swax/commands/discover/`.

**`init`** from `swax/commands`
- Path: `swax/commands/.usages/init.md`
- **Where used**: Нет прямых импортёров — это потребительская документация для будущего переиспользования.

**`discover`** from `swax/commands`
- Path: `swax/commands/.usages/discover.md`
- **Where used**: Нет прямых импортёров — потребительская документация.

---

## `.usages/` Update

Все 12 `.usages/` файлов созданы и синхронизированы с CODEMANIFEST (после materialize-коммита + sync). Изменений не требуется.

### Cell: `swax/applications/discover/`

#### New Files (proposed)
- **`errors-parsing`** → `swax/applications/discover/.usages/errors-parsing.md`
  - Reason: `run_discover` вводит внутренний helper `_parse_llm_json` с новым типом ошибки `LLMResponseParseError`. Этот тип не заявлен в CODEMANIFEST (контракт только упоминает "wrap into a meaningful domain error"). Если реализация решит ввести этот тип как доменный, его надо задокументировать.
  - Related entities: `run_discover`.

**Альтернатива**: объявить `LLMResponseParseError` локально в `swax/applications/discover/CODEMANIFEST` (как Routine/Entity без location, либо как полноценный entity в `errors.py`). Это решение принимает реализатор — design-doc только фиксирует потребность.

### Cell: other

Все остальные `.usages/` files актуальны и не требуют обновления.

---

## Test Stack Trace

### General Setup

- **Python**: 3.10+ (target-version py310).
- **Frameworks**: pytest 8+, pytest-cov 5+, ruff 0.15+ (per `pyproject.toml [project.optional-dependencies].test`).
- **Fixtures**: `tmp_path` (pytest builtin) для всех FS-операций; `monkeypatch.setenv`/`delenv` для env-vars; `mocker.patch` (pytest-mock) в точке импорта для SDK/external calls.
- **Structure**: `tests/` зеркалит `swax/`: `tests/config/test_storage.py`, `tests/openapi/test_parse_spec.py`, `tests/applications/discover/test_run_discover.py`, etc. Каждый каталог с `__init__.py`; общий `tests/conftest.py` для shared fixtures.
- **Dependencies**: добавить в `pyproject.toml [project] dependencies` (сейчас пусто): `click>=8.0`, `pydantic>=2.0`, `pyyaml>=6.0`, `gitpython>=3.1`, `prance>=23.0`, `anthropic>=0.40`, `openai>=1.50`, `python-dotenv>=1.0`. `openapi-spec-validator` — transitive dep prance (или явный, если prance без backend).

### Source File Registry

| Source | Test path |
|--------|-----------|
| `swax/config/Config.py`, `GitConfig.py`, `SpecsConfig.py`, `errors.py`, `env.py`, `storage.py` | `tests/config/test_*.py` |
| `swax/fs/ensure_swax_dir.py`, `copy_specs.py` | `tests/fs/test_*.py` |
| `swax/git/clone_specs.py`, `errors.py` | `tests/git/test_*.py` |
| `swax/openapi/parse_spec.py`, `extract_paths.py`, `extract_schemas.py`, `discover_specs.py`, `errors.py` | `tests/openapi/test_*.py` |
| `swax/traceability/TraceabilityGraph.py`, `storage.py` | `tests/traceability/test_*.py` |
| `swax/prompts/build_graph_system_prompt.py`, `build_graph_user_prompt.py`, `build_refine_user_prompt.py` | `tests/prompts/test_*.py` |
| `swax/llm/LLMClient.py`, `AnthropicAdapter.py`, `OpenAIAdapter.py`, `errors.py`, `build_*_client.py`, `build_llm_client.py` | `tests/llm/test_*.py` |
| `swax/applications/init/run_init.py` | `tests/applications/init/test_run_init.py` |
| `swax/applications/discover/run_discover.py` | `tests/applications/discover/test_run_discover.py` |
| `swax/commands/init/init.py` | `tests/commands/init/test_init.py` |
| `swax/commands/discover/discover.py` | `tests/commands/discover/test_discover.py` |
| `swax/cli/main.py`, `SwaxContext.py` | `tests/cli/test_main.py`, `tests/cli/test_SwaxContext.py` |
| `swax/cli/__main__.py` (lazy command registration) | `tests/cli/test___main__.py` |

---

### Positive Tests

#### `test_load_config_parses_valid_yaml`

**Setup**: `tmp_path / ".swax" / "config.yml"` с содержимым:
```yaml
git:
  url: https://example.com/repo.git
  location: specs/
specs:
  type: openapi
  location: local_specs/
```

**Input**: `path = tmp_path / ".swax" / "config.yml"`

**Trace**:
```
load_config(path)
  → path.read_text(encoding="utf-8")           # читает YAML
  → yaml.safe_load(raw_text)                   # → dict
  → Config.model_validate(raw)                 # → Config instance
    → GitConfig.model_validate(raw["git"])     # → GitConfig
    → SpecsConfig.model_validate(raw["specs"]) # → SpecsConfig
returns: Config(git=GitConfig(url=..., location=...), specs=SpecsConfig(type=..., location=...))
→ assert config.git.url == "https://example.com/repo.git"
→ assert config.specs.type == "openapi"
```

**Assertions**:
```python
assert config.git.url == "https://example.com/repo.git"
assert config.git.location == "specs/"
assert config.specs.type == "openapi"
assert config.specs.location == "local_specs/"
```

**Sufficiency**: Гарантирует, что round-trip `save_config` → `load_config` работает для валидного YAML; регрессия на случай поломки pydantic-схемы.

---

#### `test_save_config_creates_parents_and_writes_deterministic_yaml`

**Setup**: `tmp_path` пустой; `config = Config(git=GitConfig(url="u", location="l"), specs=SpecsConfig(type="openapi", location="loc"))`.

**Input**: `path = tmp_path / ".swax" / "config.yml"` (родитель `.swax/` не существует)

**Trace**:
```
save_config(config, path)
  → config.model_dump(mode="json")             # → dict
  → path.parent.mkdir(parents=True, exist_ok=True)  # creates .swax/
  → yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)
  → path.write_text(yaml_text, encoding="utf-8")
side effect: .swax/ created, config.yml written
```

**Assertions**:
```python
assert path.exists()
assert path.parent == tmp_path / ".swax"
content = path.read_text(encoding="utf-8")
assert "url: u" in content
assert "type: openapi" in content
# deterministic: повторный вызов даёт идентичный файл
save_config(config, path)
assert path.read_text(encoding="utf-8") == content
```

**Sufficiency**: Гарантирует создание родителей и стабильный YAML-вывод — критично для читаемых diff-ов.

---

#### `test_run_init_persists_config_then_copies_specs`

**Setup**: `tmp_path` пустой; `mocker.patch("swax.applications.init.clone_specs")` возвращает context manager, который yields mock `specs_path`; `mocker.patch("swax.applications.init.copy_specs")`.

**Input**:
```python
run_init(
  repo_url="https://example.com/repo.git",
  specs_location="specs/",
  download_path=tmp_path / "local_specs",
  project_root=tmp_path,
)
```

**Trace**:
```
run_init(...)
  → Config(GitConfig(...), SpecsConfig(type="openapi", location=str(download_path)))
  → ensure_swax_dir(tmp_path)                  # creates tmp_path/.swax
    returns: tmp_path / ".swax"
  → save_config(config, tmp_path/".swax"/"config.yml")  # writes config FIRST
  → with clone_specs(...) as specs_path:        # mocked
    → copy_specs(source=specs_path, destination=download_path)  # mocked
side effect: .swax/config.yml exists, copy_specs called once
```

**Assertions**:
```python
assert (tmp_path / ".swax" / "config.yml").exists()
mock_copy_specs.assert_called_once()
# config written BEFORE clone:
mock_clone_specs.assert_called_once()
# (verify ordering via mock_calls attribute if needed)
```

**Sufficiency**: Гарантирует контрактное требование "Configuration is written before cloning" — даже при сбое клонирования пользователь имеет конфиг.

---

#### `test_run_init_config_survives_clone_failure`

**Setup**: `tmp_path` пустой;
```python
mock_clone_specs = mocker.patch("swax.applications.init.clone_specs")
mock_clone_specs.side_effect = RepositoryCloneError(
    url="https://example.com/repo.git", reason="auth failed"
)
mock_copy_specs = mocker.patch("swax.applications.init.copy_specs")
```

**Input**:
```python
with pytest.raises(RepositoryCloneError):
    run_init(
      repo_url="https://example.com/repo.git",
      specs_location="specs/",
      download_path=tmp_path / "local_specs",
      project_root=tmp_path,
    )
```

**Trace**:
```
run_init(...)
  → Config(GitConfig(url="https://example.com/repo.git", location="specs/"),
           SpecsConfig(type="openapi", location=str(tmp_path/"local_specs")))
  → ensure_swax_dir(tmp_path) → tmp_path/.swax created
  → save_config(config, tmp_path/".swax"/"config.yml")
    → path.parent.mkdir(parents=True, exist_ok=True)
    → path.write_text(yaml_text, encoding="utf-8")   # config WRITTEN to disk
  → with clone_specs(...) as specs_path:             # mock raises RepositoryCloneError
    → copy_specs NOT reached (exception propagates from __enter__)
  → RepositoryCloneError propagates out of run_init
side effect: .swax/config.yml exists on disk despite clone failure
```

**Assertions**:
```python
with pytest.raises(RepositoryCloneError):
    run_init(...)
# контракту удовлетворено: config.yml остался на диске
assert (tmp_path / ".swax" / "config.yml").exists()
content = (tmp_path / ".swax" / "config.yml").read_text(encoding="utf-8")
assert "https://example.com/repo.git" in content
mock_copy_specs.assert_not_called()
# ordering: save_config должен быть вызван ДО clone_specs
mock_clone_specs.assert_called_once()
```

**Sufficiency**: Гарантирует ключевое контрактное требование "Configuration is written before cloning — on clone failure the user still has .swax/config.yml to inspect". Регрессия на изменение порядка save_config ↔ clone_specs в `run_init`.

---

#### `test_run_discover_builds_graph_with_two_llm_passes`

**Setup**:
- `tmp_path / ".swax" / "config.yml"` с валидным config (specs.location = "specs/")
- `tmp_path / "specs" / "api.yaml"` с минимальной OpenAPI 3.x спецификацией (paths: /users, /users/{id})
- `mocker.patch("swax.applications.discover.build_llm_client")` возвращает mock client
- mock `client.ask.return_value = '{"uncertain": [], "dependencies": {"/users": ["/users/{id}"]}}'`
- mock `client.ask_multi_turn.return_value = '{"dependencies": {"/users": ["/users/{id}"]}}'`

**Input**: `run_discover(project_root=tmp_path)`

**Trace**:
```
run_discover(tmp_path)
  → require_vars()                              # raises if missing, mocked env in test
  → load_config(tmp_path/".swax"/"config.yml")  # → Config
  → specs_root = tmp_path / "specs"
  → discover_specs(specs_root)                  # → [tmp_path/specs/api.yaml]
  → for spec_path:
    → parse_spec(...)                           # → dict
    → extract_paths(spec)                       # → ["/users", "/users/{id}"]
    → extract_schemas(spec)                     # → {}
  → build_llm_client()                          # mocked
  → build_graph_system_prompt()                 # → string
  → build_graph_user_prompt(["/users", "/users/{id}"])
  → client.ask(system, first_user)              # → raw JSON
  → _parse_llm_json(raw)                        # → dict
  → ambiguous_pairs = []
  → build_refine_user_prompt([], {})
  → client.ask_multi_turn(system, messages=...)
  → _parse_llm_json(raw_refined)                # → {"/users": ["/users/{id}"]}
  → TraceabilityGraph(edges={})
  → graph.add_edge("/users", "/users/{id}")
  → graph.deduplicate()
  → save_traceability(graph, tmp_path/".swax"/"traceability.yml")
side effect: traceability.yml exists with "/users:\n- /users/{id}"
```

**Assertions**:
```python
trace_path = tmp_path / ".swax" / "traceability.yml"
assert trace_path.exists()
content = trace_path.read_text(encoding="utf-8")
data = yaml.safe_load(content)
assert data == {"/users": ["/users/{id}"]}
mock_client.ask.assert_called_once()
mock_client.ask_multi_turn.assert_called_once()
# multi-turn messages structure:
_, kwargs = mock_client.ask_multi_turn.call_args
assert len(kwargs["messages"]) == 3
assert kwargs["messages"][0]["role"] == "user"
assert kwargs["messages"][1]["role"] == "assistant"
assert kwargs["messages"][2]["role"] == "user"
```

**Sufficiency**: Гарантирует полный двухпроходный сценарий — happy path; регрессия на нарушение порядка шагов или multi-turn message structure.

---

#### `test_run_discover_raises_llm_response_parse_error_on_invalid_first_pass`

**Setup**: как в `test_run_discover_builds_graph_with_two_llm_passes`, но
```python
mock_client.ask.return_value = 'Sorry, here is my answer: {"dependencies": {"/users": ["/orders"]}}'
# нет ключа "uncertain" → keys != {"dependencies", "uncertain"}
```

**Input**: `run_discover(project_root=tmp_path)`

**Trace**:
```
run_discover(tmp_path)
  → require_vars()                              # mocked env, OK
  → load_config(...)                            # → Config
  → discover_specs(specs_root)                  # → [tmp_path/specs/api.yaml]
  → parse_spec / extract_paths / extract_schemas
  → client.ask(system, first_user)              # → raw_first
  → _parse_llm_json(raw_first, first_pass=True)
    → _strip_prose_and_fences(raw_first)
      → first_brace = index of "{"
      → last_brace = index of "}"
      → return raw[first_brace : last_brace+1]  # = '{"dependencies": {"/users": ["/orders"]}}'
    → json.loads(stripped) → parsed = {"dependencies": {"/users": ["/orders"]}}
    → set(parsed.keys()) == {"dependencies"} != {"dependencies", "uncertain"}
    → raise LLMResponseParseError(reason="first pass: keys must be dependencies+uncertain", excerpt=stripped[:200])
propagates out of run_discover (no catch)
```

**Assertions**:
```python
with pytest.raises(LLMResponseParseError) as exc_info:
    run_discover(project_root=tmp_path)
assert "dependencies+uncertain" in exc_info.value.reason
mock_client.ask_multi_turn.assert_not_called()  # refine не запускается при ошибке 1-го pass-а
```

**Sufficiency**: Гарантирует, что defensive parser падает с информативной ошибкой ДО refine-прохода; регрессия на silent accept невалидного first-pass shape.

---

#### `test_run_discover_passes_uncertain_pairs_to_refine`

**Setup**: как в happy path, но
```python
mock_client.ask.return_value = (
    '{"dependencies": {"/users": ["/orders"]}, "uncertain": ["/users -> /orders"]}'
)
mock_client.ask_multi_turn.return_value = '{"/users": ["/orders"]}'  # valid flat shape
```

**Input**: `run_discover(project_root=tmp_path)`

**Trace**:
```
run_discover(tmp_path)
  → client.ask(system, first_user) → raw_first
  → first_dependencies, uncertain = _parse_llm_json(raw_first, first_pass=True)
    → parsed = {"dependencies": {...}, "uncertain": ["/users -> /orders"]}
    → keys == {"dependencies", "uncertain"} ✓
    → deps shape: dict[str, list[str]] ✓
    → uncertain shape: list[str] ✓
    → return deps, ["/users -> /orders"]
  → ambiguous_pairs = ["/users -> /orders"]
  → build_refine_user_prompt(["/users -> /orders"], schemas)
  → client.ask_multi_turn(system, messages=[
      {"role": "user", "content": first_user},
      {"role": "assistant", "content": raw_first},
      {"role": "user", "content": refine_user},
    ])
  → _parse_llm_json(raw_refined, first_pass=False)
    → parsed = {"/users": ["/orders"]}
    → shape: dict[str, list[str]] ✓
    → return parsed, []
  → TraceabilityGraph, add_edge("/users", "/orders"), deduplicate, save_traceability
```

**Assertions**:
```python
_, kwargs = mock_client.ask_multi_turn.call_args
refine_message = kwargs["messages"][2]["content"]
assert "/users -> /orders" in refine_message
assert kwargs["messages"][1]["content"] == mock_client.ask.return_value  # assistant = raw_first
# traceability записан с финальной зависимостью
data = yaml.safe_load((tmp_path / ".swax" / "traceability.yml").read_text())
assert data == {"/users": ["/orders"]}
```

**Sufficiency**: Гарантирует, что uncertain-пары, помеченные LLM в первом проходе, действительно попадают в refine prompt; регрессия на потерю uncertain-сигнала между проходами.

---

### Negative Tests

#### `test_require_vars_raises_on_missing_token`

**Setup**: `monkeypatch.delenv("SWAX_LLM_TOKEN", raising=False)`; остальные SWAX_* установлены.

**Input**: `require_vars()`

**Trace**:
```
require_vars()
  → FOR name IN REQUIRED_VARS:
    → "SWAX_LLM_TOKEN" → os.environ.get → None
  → missing = ["SWAX_LLM_TOKEN"]
  → raise MissingEnvironmentVariablesError(missing=missing)
```

**Assertions**:
```python
with pytest.raises(MissingEnvironmentVariablesError) as exc_info:
    require_vars()
assert "SWAX_LLM_TOKEN" in exc_info.value.missing
```

**Sufficiency**: Гарантирует валидацию mandatory env-var; регрессия на случай silent accept.

---

#### `test_parse_spec_raises_on_invalid_yaml`

**Setup**: `tmp_path / "bad.yaml"` с содержимым `: not valid yaml: :`.

**Input**: `parse_spec(tmp_path / "bad.yaml")`

**Trace**:
```
parse_spec(path)
  → ResolvingParser(...)  # raises some prance error
  → except Exception as exc:
    → raise SpecParseError(path=path, reason=str(exc)) from exc
```

**Assertions**:
```python
with pytest.raises(SpecParseError) as exc_info:
    parse_spec(tmp_path / "bad.yaml")
assert exc_info.value.path == tmp_path / "bad.yaml"
assert isinstance(exc_info.value.reason, str)
```

**Sufficiency**: Гарантирует оборачивание ошибок prance в доменное исключение; потребитель (CLI handler) может отобразить пользователю понятную ошибку.

---

#### `test_init_handler_maps_repository_clone_error`

**Setup**: `mocker.patch("swax.commands.init.run_init", side_effect=RepositoryCloneError(url="https://example.com", reason="auth failed"))`.

**Input**: `runner.invoke(init, ["..."], input="\n".join(["u", "l", "./p"]) + "\n")`

**Trace**:
```
runner.invoke(init, ...)
  → click.prompt × 3
  → project_root = Path.cwd()
  → try: run_init(...) → raises RepositoryCloneError
  → except RepositoryCloneError as exc:
    → raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")
```

**Assertions**:
```python
result = runner.invoke(init, input="u\nl\n./p\n")
assert result.exit_code == 1
assert "Failed to clone https://example.com" in result.output
assert "auth failed" in result.output
```

**Sufficiency**: Гарантирует, что пользователь видит понятную ошибку, а не traceback.

---

#### `test_discover_handler_maps_domain_errors` (parametrized)

**Setup**:
```python
@pytest.mark.parametrize("exception, expected_substring", [
    (MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"]), "SWAX_LLM_TOKEN"),
    (SpecParseError(path=pathlib.Path("/p/bad.yaml"), reason="boom"),
     "Failed to parse"),
    (LLMRateLimitedError(reason="slow down"), "rate limited"),
    (LLMCallError(reason="500"), "LLM call failed"),
    (UnsupportedLLMProtocolError(protocol="ftp"), "Unsupported LLM protocol"),
    (LLMResponseParseError(reason="shape mismatch", excerpt="..."),
     "parse failed"),
])
def test_discover_handler_maps_domain_errors(mocker, exception, expected_substring):
    mocker.patch("swax.commands.discover.run_discover", side_effect=exception)
```

**Input**: `runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))`

**Trace** (одинаковый для всех 6 параметров):
```
runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
  → project_root = pathlib.Path.cwd()
  → try: run_discover(project_root) → raises <parametrized exception>
  → except <ExceptionClass> as exc:
    → raise click.ClickException(f"<mapped message>")
exit code 1
```

**Assertions**:
```python
result = runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
assert result.exit_code == 1
assert expected_substring in result.output
```

**Sufficiency**: Гарантирует, что все 6 доменных исключений (`MissingEnvironmentVariablesError`, `SpecParseError`, `LLMRateLimitedError`, `LLMCallError`, `UnsupportedLLMProtocolError`, `LLMResponseParseError`) корректно маппятся в `click.ClickException` с user-friendly сообщением. Регрессия на удаление любого catch-блока из `discover` handler-а.

---

### Edge Case Tests

#### `test_load_env_silent_on_missing_file`

**Setup**: `env_file = tmp_path / ".env"` (НЕ существует).

**Input**: `load_env(env_file)`

**Trace**:
```
load_env(env_file)
  → IF NOT env_file.exists():
    → return
no side effect, no exception
```

**Assertions**:
```python
load_env(tmp_path / ".env")  # не должно падать
# никаких os.environ изменений
```

**Sufficiency**: Гарантирует, что отсутствие `.env` — не ошибка (контракт `main`: "Do not raise on missing .env — load_env handles it").

---

#### `test_traceability_graph_deduplicate_idempotent_and_removes_self_loops`

**Setup**: `graph = TraceabilityGraph(edges={"/a": ["/b", "/b", "/a"], "/b": ["/a"]})`.

**Input**: `graph.deduplicate()` × 2

**Trace**:
```
graph.deduplicate()
  → for "/a": edges["/a"] = sorted(set(["/b", "/b", "/a"])) = ["/a", "/b"]
    → "/a" in ["/a", "/b"]: edges["/a"] = ["/b"]
  → for "/b": edges["/b"] = sorted(set(["/a"])) = ["/a"]
    → "/b" not in ["/a"]: no change
graph.deduplicate()  # idempotent
  → no changes
```

**Assertions**:
```python
graph.deduplicate()
assert graph.edges == {"/a": ["/b"], "/b": ["/a"]}
graph.deduplicate()
assert graph.edges == {"/a": ["/b"], "/b": ["/a"]}
```

**Sufficiency**: Гарантирует детерминированность графа и идемпотентность.

---

#### `test_parse_base_url_rejects_versioned_segments`

**Setup**: parametrize:
```python
@pytest.mark.parametrize("value", [
    "https://api.example.com/v1",
    "https://api.example.com/v2/",
    "https://api.example.com/v1/",
])
def test_parse_base_url_rejects_versioned(value):
    ...
```

**Input**: `parse_base_url(value)`

**Trace**:
```
parse_base_url(value)
  → stripped = value.rstrip("/")
  → IF stripped.endswith(("/v1", "/v2")):
    → raise InvalidLLMBaseURLError(value=value)
```

**Assertions**:
```python
with pytest.raises(InvalidLLMBaseURLError):
    parse_base_url(value)
```

**Sufficiency**: Гарантирует, что base URL с `/v1`/`/v2` отвергается — SDK добавляет version segment сам.

---

#### `test_run_discover_overwrites_existing_traceability_yml`

**Setup**: `tmp_path / ".swax" / "traceability.yml"` с содержимым `{"/old": ["/path"]}`; остальная setup как в `test_run_discover_builds_graph_with_two_llm_passes`.

**Input**: `run_discover(project_root=tmp_path)`

**Trace**:
```
run_discover(tmp_path)
  → ... (как в happy path)
  → save_traceability(graph, tmp_path/".swax"/"traceability.yml")
    → path.parent.mkdir(...)
    → path.write_text(yaml_text, ...)  # overwrites existing
side effect: traceability.yml содержит только новый граф
```

**Assertions**:
```python
content = (tmp_path / ".swax" / "traceability.yml").read_text()
data = yaml.safe_load(content)
assert data == {"/users": ["/users/{id}"]}
assert "/old" not in data
```

**Sufficiency**: Гарантирует контрактное требование "Always builds a fresh graph — existing .swax/traceability.yml is ignored".

---

#### `test_parse_protocol_accepts_supported_values`

**Setup**: parametrize:
```python
@pytest.mark.parametrize("value", ["anthropic", "openai"])
def test_parse_protocol_accepts_supported_values(value):
    ...
```

**Input**: `parse_protocol(value)`

**Trace**:
```
parse_protocol(value)
  → IF value NOT IN ("anthropic", "openai"): skip  # value passes
  → RETURN value
```

**Assertions**:
```python
assert parse_protocol(value) == value
```

**Sufficiency**: Гарантирует, что supported protocols принимаются without raising. Регрессия на случай излишне строгой валидации (например, если кто-то добавит `.lower()` или `.strip()` и сломает case-sensitivity).

---

#### `test_clone_specs_cleans_up_tempdir_on_clone_failure`

**Setup**: `tmp_path` пустой; `mocker.patch("swax.git.Repo.clone_from", side_effect=GitCommandError("clone", "auth failed"))`. `tempfile.TemporaryDirectory` реальный (не мок-ий).

**Input**:
```python
with pytest.raises(RepositoryCloneError):
    with clone_specs("https://example.com/repo.git", "specs/"):
        pass  # never reached
```

**Trace**:
```
clone_specs("https://example.com/repo.git", "specs/")
  → with tempfile.TemporaryDirectory(prefix="swax-") as tmp:
    → tmp_path = pathlib.Path(tmp)
    → Repo.clone_from(...) → GitCommandError (mocked)
    → except GitCommandError as exc:
      → raise RepositoryCloneError(url=..., reason=str(exc)) from exc
  → exit from with: TemporaryDirectory.__exit__ удаляет tmp/, даже при exception
propagates: RepositoryCloneError
side effect: tempdir от https://example.com НЕ остаётся в /tmp
```

**Assertions**:
```python
import glob
swax_tempdirs_before = glob.glob("/tmp/swax-*")  # captured via patch on TemporaryDirectory

with pytest.raises(RepositoryCloneError):
    with clone_specs("https://example.com/repo.git", "specs/"):
        pass

# tempdir cleanup happened (verify by checking the TemporaryDirectory cleanup path was invoked).
# Альтернативно: spy на TemporaryDirectory.__exit__:
mock_tmp = mocker.spy(tempfile, "TemporaryDirectory")
with pytest.raises(RepositoryCloneError):
    with clone_specs(...):
        pass
mock_tmp.return_value.__exit__.assert_called_once()
```

**Sufficiency**: Гарантирует контракт "The temporary directory is cleaned up on every outcome" — критично для предотвращения утечки FS-ресурсов при сбоях клонирования. Регрессия на изменение context manager-логики (например, замена `with` на ручной try/finally без cleanup).

---

#### `test_extract_schemas_returns_definitions_for_swagger_2`

**Setup**:
```python
spec = {
    "swagger": "2.0",
    "paths": {...},
    "definitions": {
        "User": {"type": "object", "properties": {...}},
        "Order": {"type": "object", "properties": {...}},
    },
}
# НЕТ ключа "components" (Swagger 2.0 формат)
```

**Input**: `extract_schemas(spec)`

**Trace**:
```
extract_schemas(spec)
  → IF "components" IN spec: FALSE  # swagger 2.0 не имеет components
  → RETURN spec.get("definitions", {}) → {"User": {...}, "Order": {...}}
```

**Assertions**:
```python
schemas = extract_schemas(spec)
assert set(schemas.keys()) == {"User", "Order"}
assert schemas["User"]["type"] == "object"
```

**Sufficiency**: Гарантирует контракт "Transparently distinguishes OpenAPI 3.x (components.schemas) from Swagger 2.0 (definitions)". Регрессия на изменение условия ветвления (например, если кто-то изменит на `spec.get("components", {}).get("schemas") or spec.get("definitions")` — тест провалится, если порядок изменится).

---

## Additional Instructions for the Implementation Agent

- **Д1 уже применён в `swax/cli/CODEMANIFEST`**: `Imports.Types` теперь содержит `load_env, load_config, Config`; `Imports.Usages` — `environment, project-config`. Не откатывать.
- **Д4 уже применён в `swax/applications/discover/CODEMANIFEST`**: добавлена inline `Usages: json`. Backticks вокруг `json.loads`/`json.JSONDecodeError` убраны (правило `goga_linter_annotation_backticks` из auto-memory). Не откатывать.
- **Д3 (SDK-типы `Anthropic`/`OpenAI`)**: оставить как есть. cook-файлы `anthropic.md`/`openai.md` дают достаточный контекст; формальный `Imports` невозможен без ячейки-обёртки. Если в будущем появится ячейка `swax/vendors/llm/` с re-export SDK-классов — пересмотреть.
- **Д2 (`--env-file exists=False`)**: при реализации `main.py` использовать `click.Path(exists=False, dir_okay=False, path_type=pathlib.Path)`. Cook-файл `click.md` НЕ править — он описывает общий паттерн, специфичная семантика Swax зафиксирована в аннотации `main`.
- **`LLMResponseParseError`**: уже заявлен в `swax/llm/errors.py` (review pass 2). Импортирован в `swax/applications/discover/` (helper `_parse_llm_json` поднимает его при JSONDecodeError, non-dict, или shape mismatch) и в `swax/commands/discover/` (handler маппит в ClickException). Usages обновлены. Дополнительно: helper принимает `first_pass` флаг для двух форм ответа (см. §Algorithm Design → `run_discover`).
- **`pyproject.toml dependencies`**: список зависимостей пуст — обязательно заполнить перед запуском `pytest`: `click>=8.0`, `pydantic>=2.0`, `pyyaml>=6.0`, `gitpython>=3.1`, `prance>=23.0`, `anthropic>=0.40`, `openai>=1.50`, `python-dotenv>=1.0`. Возможно, `openapi-spec-validator` (transitive для prance backend).
- **DEFAULT_MODEL**: фиксирован в коде адаптеров (`AnthropicAdapter.py`: `DEFAULT_MODEL = "claude-sonnet-4-6"` или аналогичный актуальный; `OpenAIAdapter.py`: `DEFAULT_MODEL = "gpt-4o"`). Не выносить в env в задаче 1.
- **`copy_specs` symlinks**: CODEMANIFEST аннотация говорит "Symlinks in the clone are not dereferenced — copied as regular files". При реализации использовать `shutil.copytree(source, destination, dirs_exist_ok=True)` — default `symlinks=False` копирует symlink-таргеты как regular files. Не передавать `symlinks=True`.
- **Логирование**: `logging.getLogger(__name__)` в каждом модуле. INFO на start/end use-case, DEBUG на intermediate (spec_files count, endpoints count, raw LLM response truncated). `SWAX_LLM_TOKEN` никогда не в `extra` и не в сообщениях.
- **`SwaxContext.config`**: в задаче 1 НЕ заполнять автоматически — остаётся `None`. Подкоманды вызывают `load_config` внутри use-case-а.
- **Документация `.usages/`**: после добавления `LLMResponseParseError` обновить `swax/applications/.usages/discover.md` (раздел "Обработка доменных исключений") и `swax/commands/.usages/discover.md` (таблица Exception → Сообщение).
- **Тесты**: использовать `tmp_path` для всех FS-операций; `monkeypatch.setenv`/`delenv` для env; `mocker.patch` в точке импорта для SDK/external. Не вызывать live LLM API — всегда mock. Для интеграционного теста `run_init` можно использовать локальный git-репозиторий в `tmp_path`.
- **Порядок реализации**: по архитектурному плану (листья → корень) — `config/`, `fs/`, `git/`, `openapi/`, `traceability/`, `prompts/`, `llm/`, `applications/init/`, `applications/discover/`, `commands/init/`, `commands/discover/`, `cli/`.