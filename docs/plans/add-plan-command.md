# Plan: `add-plan-command`

## Purpose

Реализация команды `swax plan` — анализ различий между локальными (базовыми)
спецификациями и свежим состоянием репозитория, маппинг изменений на граф
отслеживаемости и формирование Markdown Impact Report о влиянии изменений на
тестирование (вывод в stdout).

После выполнения плана проект предоставляет:
- доменную diff-подсистему в клетке `swax/openapi` (`diff_specs`,
  `classify_endpoint_changes`, `EndpointDiff`) поверх `deepdiff`;
- обход графа и доменную ошибку в клетке `swax/traceability`
  (`find_affected_endpoints`, `TraceabilityGraphMissingError`);
- два routine-билдера промптов в клетке `swax/prompts`
  (`build_impact_report_system_prompt`, `build_impact_report_user_prompt`);
- use-case-клетку `swax/applications/plan` (`run_plan`, `ImpactReport`,
  `render_impact_report`) — single-turn LLM-сценарий по образцу `run_discover`;
- тонкий command-обработчик `swax/commands/plan` (`plan`) с маппингом 9 доменных
  ошибок;
- регистрацию `plan` на группе `main` (уже выполнена в `swax/cli/__main__.py`
  предыдущей стадией — **не модифицируется**).

Стратегия реализации — bottom-up: доменные листья (`openapi` diff →
`traceability` traversal → `prompts`) → use-case `applications/plan` →
command-handler `commands/plan` → integration. В каждой coding-задаче сначала
пишутся контракт-тесты (фасад, сигнатуры), затем код, затем interface
verification, затем логические тесты. `CODEMANIFEST`-файлы и `.usages/` уже
материализованы и считаются **read-only**.

## Context

### Contract Surface

Источник истины — материализованные `CODEMANIFEST` на ветке `add-plan-command`
(`goga lint` → 16 cells, 0 errors). Ниже — per-cell контрактные сущности с
`location`, фасадными обязательствами и ключевыми требованиями. Полные сигнатуры
и алгоритмы — в соответствующих `CODEMANIFEST` и в `docs/design/add-plan-command.md`
(§Algorithm Design, §Code Stack Trace, §Test Stack Trace).

**Cell: `swax/openapi/`** (modified — новый diff-подсистемный блок)
- `EndpointDiff(added: list[str], removed: list[str], modified: dict[str, list[str]])`
  — Entity, `endpoint_diff.py`, pydantic `kw_only=True`
  - property `added -> list[str]`, property `removed -> list[str]`,
    property `modified -> dict[str, list[str]]`
  - method `has_changes() -> changed: bool` — `True`, когда любой из трёх
    контейнеров непуст
  - method `changed_paths() -> paths: list[str]` —
    `sorted(set(added) | set(removed) | set(modified.keys()))` (детерминированный,
    дедуплицированный)
- `diff_specs(base: dict, current: dict) -> diff: DeepDiff` — Routine,
  `diff_specs.py` (один вызов `DeepDiff` с зафиксированными kwargs; классификацию
  НЕ делает)
- `classify_endpoint_changes(diff: DeepDiff) -> changes: EndpointDiff` — Routine,
  `classify_endpoint_changes.py` (читает `dictionary_item_added` /
  `dictionary_item_removed` / `values_changed` / `type_changes` по path-строкам;
  пути под `paths` → added/removed/modified; пути под `components`/`definitions`
  → skip, т.к. `$ref` уже развёрнут)
  - приватные helper-ы вне контракта: `_extract_endpoint(path_str) -> str | None`,
    `_describe_change(path_str) -> str`
- Фасад: `diff_specs`, `classify_endpoint_changes`, `EndpointDiff` добавить в
  `swax/openapi/__init__.py.__all__` (вместе с уже существующими 5 именами)
- Usages: `conventions`, `prance`, `pyyaml`, **`deepdiff` (новый)**

**Cell: `swax/traceability/`** (modified — traversal + missing-graph error; cell
остаётся без cross-cell `Imports`)
- `find_affected_endpoints(changed_paths: list[str], graph: TraceabilityGraph) -> affected: list[str]`
  — Routine, `find_affected_endpoints.py` (обратная достижимость: changed + все
    транзитивные dependents; read-only; принимает plain path strings)
- `TraceabilityGraphMissingError(path: pathlib.Path)` — Entity, `errors.py`
  (keyword-only `Exception`; `.path` как публичный атрибут)
- Фасад: `find_affected_endpoints`, `TraceabilityGraphMissingError` добавить в
  `swax/traceability/__init__.py.__all__`
- Usages: `conventions`, `pyyaml`

**Cell: `swax/prompts/`** (modified — impact-report builders; cell остаётся import-free)
- `build_impact_report_system_prompt() -> prompt: str` — Routine,
  `build_impact_report_system_prompt.py` (константный system prompt: роль
  impact-analyst, JSON-контракт из 6 ключей, `risk ∈ {HIGH,MEDIUM,LOW}`,
  «JSON only — no prose»)
- `build_impact_report_user_prompt(added: list[str], removed: list[str], modified: dict[str, list[str]], affected: list[str], graph_context: dict[str, list[str]]) -> prompt: str`
  — Routine, `build_impact_report_user_prompt.py` (рендер пяти примитивов через
    `json.dumps`; без silent truncation)
- Фасад: оба имени добавить в `swax/prompts/__init__.py.__all__`
- Usages: `conventions`

**Cell: `swax/applications/plan/`** (new use-case cell; Imports из `config`, `git`,
`openapi`, `traceability`, `prompts`, `llm` — шесть групп)
- `ImpactReport(summary: str, risk: str, modified: list[str], affected: list[str], requirements: list[str], checklist: list[str])`
  — Entity, `impact_report.py`, pydantic `kw_only=True` (6 полей; без методов)
- `render_impact_report(report: ImpactReport) -> markdown: str` — Routine,
  `render_impact_report.py` (чистая трансформация в Markdown-шаблон; пустые
  секции рендерятся как «(none)»)
- `run_plan(project_root: pathlib.Path) -> markdown: str` — Routine, `run_plan.py`
  (10-шаговый оркестратор — см. Interaction Diagram в design-doc; defensive JSON
  parse + risk fallback MEDIUM)
  - приватные helper-ы вне контракта: `_parse_spec_map(paths, root)`,
    `_diff_and_classify(baseline, fresh)`,
    `_build_graph_context(affected, changed, graph)`,
    `_parse_impact_report(raw)`
- Фасад: `run_plan` в `swax/applications/plan/__init__.py.__all__`
- Usages: `conventions`; inline `json`

**Cell: `swax/applications/`** (modified facade)
- Re-export: `->run_plan_handler: {}` (новый), backed by
  `run_plan AS run_plan_handler` из `swax/applications/plan`
- Фасад: добавить `from .plan import run_plan as run_plan_handler` и расширить
  `__all__` в `swax/applications/__init__.py` (уже содержит
  `run_init_handler`, `run_discover_handler`)

**Cell: `swax/commands/plan/`** (new command cell; Imports из `applications`,
`cli`, и доменных error-типов из `config` / `openapi` / `git` / `traceability` / `llm`)
- `plan(ctx: SwaxContext)` — Routine (Click command), `plan.py` (thin handler:
  delegate → echo → map 9 доменных ошибок; `SwaxContext` под `TYPE_CHECKING`)

**Cell: `swax/commands/`** (modified facade)
- Re-export: `->plan_handler: {}` (новый), backed by
  `plan AS plan_handler` из `swax/commands/plan`
- Фасад: добавить `from .plan import plan as plan_handler` и расширить `__all__`
  в `swax/commands/__init__.py` (уже содержит `init_handler`, `discover_handler`)

**Cell: `swax/cli/`** — **без работы**. `swax/cli/__main__.py` уже импортирует
`plan_handler` и регистрирует `main.add_command(plan_handler, name="plan")`
(выполнено предыдущей стадией по выбору пользователя A). `swax/cli/CODEMANIFEST`
уже описывает lazy-регистрацию `init`/`discover`/`plan`.

### Re-exports

| Re-export | Source | Facade |
|-----------|--------|--------|
| `run_plan_handler` | `run_plan AS run_plan_handler` из `swax/applications/plan` | `swax/applications` |
| `plan_handler` | `plan AS plan_handler` из `swax/commands/plan` | `swax/commands` |

Иерархический constraint: source каждого re-export находится уровнем ниже фасада.
`swax/cli/__main__.py` импортирует `plan_handler` из фасада `swax/commands`, поэтому
**обязательны** оба фасадных обновления (`applications` и `commands`) — иначе
`swax plan` упадёт с `ImportError` на этапе импорта.

### Usages Context

**Project-level (`.goga/usages/`)**
- `conventions` — Python code rules: relative intra-package imports, pydantic
  `kw_only=True`, Google-style docstrings, stdlib `logging` со structured
  `extra`, blank-line block separation, тестовый слой `tests/` зеркалит `swax/`,
  `tmp_path`/`monkeypatch`/`mocker`, split `*_contract.py` / `*_logic.py`,
  `pytest`/`ruff` команды.
- `deepdiff` — `DeepDiff(base, current, ignore_order=True, report_repetition=False,
  cutoff_intersection_for_pairs=1, verbose_level=1)`; change-set accessor-ы
  `dictionary_item_added` / `dictionary_item_removed` (ordered sets of path
  strings) и `values_changed` / `type_changes` (dicts keyed by path).
  **Категорий `keys_added` / `keys_removed` в deepdiff 8.x/9.x НЕТ** (эмпирически
  верифицировано на `deepdiff==9.1.0` стадией design-review). Детерминированный
  assert-паттерн (без mock).
- `click` — `@click.command()`, `@click.pass_obj`, `click.echo`,
  `click.ClickException`, `click.testing.CliRunner`.

### Imported Usages (cell-level)

Потребитель `run_plan` читает practice-файлы шести provider-клеток (tracked
cross-cell links, не контрактные обязательства):

| Usage | From cell | Relevance |
|-------|-----------|-----------|
| `project-config`, `environment` | `swax/config` | `load_config` / `Config` shape; `require_vars` fail-fast |
| `specs-repository` | `swax/git` | `clone_specs` ctx-mgr + `RepositoryCloneError` / `SpecsNotFoundError` |
| `parsing`, `diff` | `swax/openapi` | `discover_specs` / `parse_spec` и новые `diff_specs` / `classify_endpoint_changes` / `EndpointDiff` |
| `graph-lifecycle`, `affected-endpoints` | `swax/traceability` | `load_traceability` / `TraceabilityGraph` и новые `find_affected_endpoints` / `TraceabilityGraphMissingError` |
| `impact-report-prompts` | `swax/prompts` | `build_impact_report_system_prompt` / `build_impact_report_user_prompt` |
| `llm-transport` | `swax/llm` | `build_llm_client` / `LLMClient.ask` + LLM error-типы |
| `cli-facade` | `swax/cli` (consumed by `commands/plan`) | паттерн доступа `SwaxContext` |
| `plan` (alias `plan-usage`) | `swax/applications` (consumed by `commands/plan`) | семантика `run_plan` |

### Local Usages

Пять consumer-facing `.usages/` файлов уже созданы стадией `apply-architecture` и
синхронизированы с материализованным CODEMANIFEST (статус **current** — см.
`.usages/ Update` в design-doc). В этом плане новых `.usages/` файлов не
создаётся, существующие **не редактируются** (read-only).

### External Dependencies

- Сторонние (новая): **`deepdiff>=8.0`** — добавить в `pyproject.toml`
  `[project.dependencies]` (сейчас отсутствует; `openapi/CODEMANIFEST`
  ссылается на `deepdiff` usage, а `diff_specs` его импортирует).
- Сторонние (существующие): `click>=8.0`, `pydantic>=2.0`, `pyyaml>=6.0`,
  `gitpython>=3.1`, `prance>=23.0,<24`, `anthropic>=0.40`, `openai>=1.50`,
  `python-dotenv>=1.0`.
- Stdlib: `pathlib`, `json`, `logging`, `typing`.
- Тестовые: `pytest>=8.0`, `pytest-mock>=3.10`, `ruff>=0.15.0` (уже в `[test]`).

## Facts

- Версия Python: `>=3.10` (`pyproject.toml`). Используется `typing.Optional`
  (правило `UP045` отключено — `X | None` несовместимо с pydantic-полями на 3.10).
- Все pydantic-модели во всех клетках — `kw_only=True` (`EndpointDiff`,
  `ImpactReport`).
- Все доменные ошибки — keyword-only `Exception`-подклассы с публичными
  атрибутами (`exc.missing`, `exc.path`, `exc.reason`, `exc.url`, `exc.protocol`,
  `exc.excerpt`). `SWAX_LLM_TOKEN` никогда не попадает ни в ошибку, ни в лог, ни в
  Markdown-вывод.
- Зеркальный паттерн defensive JSON-parse уже реализован в
  `swax/applications/discover/run_discover.py` (`_strip_prose_and_fences`,
  `_parse_llm_json`, `_validate_dependency_shape`) и в handler-е
  `swax/commands/discover/discover.py` (`TYPE_CHECKING` для `SwaxContext`,
  маппинг 6 ошибок). `run_plan` / `plan` строго следуют этому образцу.
- `load_traceability` возвращает **пустой граф** для отсутствующего файла (читает
  `""`), поэтому проверку существования `.swax/traceability.yml` владеет `run_plan`
  (`traceability_path.exists()` **до** `load_traceability`) и поднимает
  `TraceabilityGraphMissingError` сам. Это зеркало паттерна
  `LLMResponseParseError` (объявлен в `llm`, поднимается в `run_discover`).
- Propagation `SpecParseError` (из `parse_spec`) и `UnsupportedLLMProtocolError`
  (из `build_llm_client`) — неявная; annotation `run_plan` их не перечисляет, но
  handler их мапит (идентично прецеденту `run_discover`).
- `graph_context` — это slice `graph.edges` для affected-путей:
  `{p: list(graph.edges.get(p, [])) for p in kept}` (для каждого affected
  эндпоинта — эндпоинты, от которых он зависит). Слово «dependents» в usage —
  свободное; authoritative derivation — slice выше.
- Context-trimming: `_MAX_AFFECTED = 100` (tuning-константа, не часть контракта).
  При превышении — `kept = changed-first (в исходном порядке) + sorted remainder`,
  truncated; триммятся **оба**: `graph_context` и `affected`, передаваемый в
  prompt; WARNING-лог.
- `clone_specs` — context manager (`tempfile.TemporaryDirectory`), cleanup
  гарантирован на любом исходе; вся diff/classify-работа со свежим клоном —
  внутри `with`-блока, наружу выходит только чистое значение `EndpointDiff`.
- `swax/cli/__main__.py` уже импортирует и регистрирует `plan_handler` — менять
  нельзя.
- `deepdiff.DeepDiff` детерминирован — assert на него напрямую (без mock).
- Тесты всегда mock-ют только внешние границы (`build_llm_client`, `clone_specs`,
  при желании `Repo.clone_from`), никогда — live LLM.

## Gap Analysis

- **Missing contract entities**: `diff_specs`, `classify_endpoint_changes`,
  `EndpointDiff` (openapi); `find_affected_endpoints`, `TraceabilityGraphMissingError`
  (traceability); `build_impact_report_system_prompt`,
  `build_impact_report_user_prompt` (prompts); `run_plan`, `ImpactReport`,
  `render_impact_report` (applications/plan); `plan` (commands/plan). Ни один из
  этих `*.py` не существует.
- **Missing facade exposure**: `swax/openapi/__init__.py`,
  `swax/traceability/__init__.py`, `swax/prompts/__init__.py` не содержат новых
  имён; `swax/applications/plan/__init__.py`, `swax/commands/plan/__init__.py`
  отсутствуют; `swax/applications/__init__.py`, `swax/commands/__init__.py` не
  содержат `run_plan_handler` / `plan_handler`.
- **Missing file `swax/traceability/errors.py`** — не существует (создаётся).
- **`location` placement**: каждый `*.py` создаётся на уровне каталога своей
  клетки.
- **Тестовый слой**: каталоги `tests/applications/plan/`, `tests/commands/plan/`
  отсутствуют; файл `tests/applications/test_applications_facade.py` отсутствует
  (создаётся); `tests/commands/test_commands_facade.py` расширяется.
- **Зависимость `pyproject.toml`**: `deepdiff` отсутствует в
  `[project.dependencies]` — добавить перед запуском тестов openapi-diff.
- **Existing code reused**: зеркальные паттерны из
  `swax/applications/discover/run_discover.py` (`_strip_prose_and_fences`,
  defensive parse) и `swax/commands/discover/discover.py` (handler + TYPE_CHECKING).

---

## Tasks

> **Package ordering rule**: задачи выполняются строго в порядке листьев → корень
> (см. таблицу ниже). Клетка `swax/cli` **исключена** — `__main__.py` уже обновлён.
> Внутри coding-задачи — TDD: контракт-тесты → код → interface verification →
> logic-тесты → debugging → contract re-verification → lint.

> **CRITICAL для всех задач**: `CODEMANIFEST` и `.usages/` — **read-only**. Если
> реализация не сходится с контрактом, фиксируйте реализацию, не контракт.

### Порядок выполнения

| # | Cell | Уровень |
|---|------|---------|
| 0 | `pyproject.toml` (bootstrap) | — |
| 1 | `swax/openapi/` — `EndpointDiff` | 0 (leaf) |
| 2 | `swax/openapi/` — `diff_specs` + `classify_endpoint_changes` + facade | 0 (leaf) |
| 3 | `swax/traceability/` — error + `find_affected_endpoints` + facade | 0 (leaf) |
| 4 | `swax/prompts/` — impact-report builders + facade | 0 (leaf) |
| 5 | `swax/applications/plan/` — `ImpactReport` + `render_impact_report` | 1 |
| 6 | `swax/applications/plan/` — `run_plan` + `__init__` + `applications` facade | 1 |
| 7 | `swax/commands/plan/` — `plan` + `__init__` + `commands` facade | 2 |
| 8 | Integration — end-to-end `swax plan` | — |

---

### Task 0: Bootstrap — добавить `deepdiff` в `pyproject.toml` (infrastructure)

`swax/openapi/CODEMANIFEST` ссылается на usage `deepdiff`, а `diff_specs`
импортирует `deepdiff.DeepDiff`. Без зависимости в `pyproject.toml` задача 2
(и весь pipeline diff) не компилируется и не тестируется.

- [x] В `pyproject.toml` секцию `[project].dependencies` добавить `deepdiff>=8.0`
  (сопроводить inline-комментарием при необходимости; совместимо с pin-стилем
  остальных зависимостей).
- [x] Переустановить пакет с тестовыми зависимостями: `pip install -e '.[test]'`
- [x] Smoke: `python -c "import deepdiff; print(deepdiff.__version__)"` — должно
      вывести версию `>=8.0` (на CI/локали верифицировано `9.1.0`).
- [x] Lint: `ruff check` — без регрессий (pyproject валиден).

---

### Task 1: `swax/openapi/` — `EndpointDiff` entity

Фундамент diff-подсистемы: pydantic-модель, которую возвращает
`classify_endpoint_changes` и которую `run_plan` использует для `has_changes()` /
`changed_paths()`. Реализуется первой, т.к. последующая задача (pipeline) и тест
`test_endpoint_diff_changed_paths_dedup_across_buckets` ссылаются на неё напрямую.

**Usages relevant to this task:**
- `conventions`: pydantic `kw_only=True` (`ConfigDict(kw_only=True)`),
  relative imports, type hints, Google-style docstring, `__all__`.

**Контрактные сущности (см. `swax/openapi/CODEMANIFEST`):**
- `EndpointDiff(added: list[str], removed: list[str], modified: dict[str, list[str]])`
  — `endpoint_diff.py`
  - properties `added` / `removed` / `modified`
  - method `has_changes() -> changed: bool`
  - method `changed_paths() -> paths: list[str]`

**Алгоритмы (перенесены verbatim из design-doc §`EndpointDiff`):**
```
has_changes():
  return bool(added or removed or modified)

changed_paths():
  return sorted(set(added) | set(removed) | set(modified.keys()))
```

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [x] **Contract tests** (`tests/openapi/test_endpoint_diff_contract.py`):
      `from swax.openapi import EndpointDiff` успешен; модель `kw_only`
      (`TypeError` на позиционные аргументы); три поля доступны как атрибуты;
      `has_changes` и `changed_paths` — callable, сигнатуры через `inspect`
      соответствуют контракту. (Ожидаемый fail — `ImportError`.)
- [x] **Code**: создать `swax/openapi/endpoint_diff.py` — pydantic-модель с
      `model_config = ConfigDict(kw_only=True)` и тремя полями; методы
      `has_changes()` / `changed_paths()` по алгоритму выше. Module-level
      `__all__: list[str] = ["EndpointDiff"]`, Google-style docstring. (`EndpointDiff`
      добавлен в фасад `swax/openapi/__init__.py` — требуется для контракт-теста
      `from swax.openapi import EndpointDiff`; оставшиеся иён фасада
      `diff_specs`/`classify_endpoint_changes` добавит Task 2.)
- [x] **Interface verification**: `pytest tests/openapi/test_endpoint_diff_contract.py -v`
- [x] **Logic tests** (`tests/openapi/test_endpoint_diff_logic.py`) — verbatim из
      design-doc edge-case test `test_endpoint_diff_changed_paths_dedup_across_buckets`:
      - `diff_a = EndpointDiff(added=["/x"], removed=[], modified={"/x": ["resp 200 changed"]})`
        → `diff_a.changed_paths() == ["/x"]` (дедуп across buckets);
        `diff_a.has_changes() is True`.
      - `diff_b = EndpointDiff(added=[], removed=[], modified={})`
        → `diff_b.has_changes() is False` (precondition no-change short-circuit).
      - Доп.: `EndpointDiff(added=["/b","/a"], removed=["/c"], modified={"/d":[]}).changed_paths() == ["/a","/b","/c","/d"]`
        (sorted union); `kw_only` enforced (`EndpointDiff(["/x"], [], {})` → `TypeError`).
- [x] **Debugging**: `pytest tests/openapi/ -v` — фиксить только код (не тесты),
      пока все тесты не пройдут.
- [x] **Contract re-verification**: `kw_only=True`; сигнатуры `has_changes` /
      `changed_paths` совпадают с контрактом; `changed_paths` детерминированный.
- [x] **Lint**: `ruff check swax/openapi/endpoint_diff.py tests/openapi/test_endpoint_diff_*.py`

---

### Task 2: `swax/openapi/` — `diff_specs` + `classify_endpoint_changes` pipeline + facade

Две routine в разных `location`, образующие один pipeline: `diff_specs` считает
сырой `DeepDiff`, `classify_endpoint_changes` превращает его в `EndpointDiff`.
Позитивный тест design-doc `test_diff_specs_detects_added_endpoint` покрывает обе.
По завершении — расширяется фасад клетки.

**Usages relevant to this task:**
- `deepdiff`: `DeepDiff(base, current, ignore_order=True, report_repetition=False,
  cutoff_intersection_for_pairs=1, verbose_level=1)`; accessor-ы
  `dictionary_item_added` / `dictionary_item_removed` (ordered sets of path
  strings) и `values_changed` / `type_changes` (dicts keyed by path). Категорий
  `keys_added` / `keys_removed` **нет** — использовать только реальные имена.
  `DeepDiff` детерминирован — assert напрямую, без mock.
- `conventions`: relative imports (`from .endpoint_diff import EndpointDiff`),
  Google-style docstrings, `__all__`.

**Контрактные сущности (см. `swax/openapi/CODEMANIFEST`):**
- `diff_specs(base: dict, current: dict) -> diff: DeepDiff` — `diff_specs.py`
- `classify_endpoint_changes(diff: DeepDiff) -> changes: EndpointDiff` —
  `classify_endpoint_changes.py`

**Внутренние helper-ы (в `classify_endpoint_changes.py`, вне контракта):**
- `_extract_endpoint(path_str) -> str | None` — вернуть эндпоинт из префикса
  `root['paths']['<endpoint>']`, иначе `None` (для `components`, `definitions`,
  `info`, `servers`, …). DeepDiff экранирует кавычки в path-ключах — парсить
  проходом по bracketed-сегментам, не наивным `split`.
- `_describe_change(path_str) -> str` — короткое человекочитаемое описание хвоста
  после эндпоинта (напр. `"GET responses.200 changed"`, `"parameters changed"`);
  lowercases/simplifies; не течёт raw dict repr.

**Алгоритмы (перенесены verbatim из design-doc §`diff_specs` / §`classify_endpoint_changes`):**

`diff_specs`:
```
1. Return DeepDiff(base, current,
     ignore_order=True,          # endpoint order is not significant
     report_repetition=False,
     cutoff_intersection_for_pairs=1,  # skip identical subtrees early (perf)
     verbose_level=1)            # never verbose_level=2 in production
   → the DeepDiff object, unchanged
```

`classify_endpoint_changes`:
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

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/openapi/test_diff_contract.py`):
      `from swax.openapi import diff_specs, classify_endpoint_changes` успешен;
      сигнатуры через `inspect` соответствуют контракту
      (`diff_specs(base, current)`, `classify_endpoint_changes(diff)`);
      `diff_specs(...)` возвращает объект с типом `deepdiff.DeepDiff`.
- [ ] **Code**: создать `swax/openapi/diff_specs.py` (одна routine, `from deepdiff import DeepDiff`,
      `__all__ = ["diff_specs"]`); `swax/openapi/classify_endpoint_changes.py`
      (routine + приватные helper-ы `_extract_endpoint` / `_describe_change`,
      `from .endpoint_diff import EndpointDiff`, `__all__ = ["classify_endpoint_changes"]`).
- [ ] **Interface verification**: `pytest tests/openapi/test_diff_contract.py -v`
- [ ] **Logic tests** (`tests/openapi/test_diff_logic.py`) — verbatim из design-doc:
      - `test_diff_specs_detects_added_endpoint` (positive):
        `base = {"paths": {"/users": {}}}`, `current = {"paths": {"/users": {}, "/orders": {}}}`;
        `changes = classify_endpoint_changes(diff_specs(base, current))`;
        `changes.added == ["/orders"]`, `changes.removed == []`, `changes.modified == {}`,
        `changes.has_changes() is True`, `"/orders" in changes.changed_paths()`.
      - `test_classify_endpoint_changes_attributes_schema_change_to_endpoint` (edge):
        dereferenced specs где изменён `paths./users.get.responses.200.schema.type`
        **и** `components.schemas.User.name`; assert `"/users" in changes.modified` и
        `all(ep.startswith("/") for ep in changes.modified)` (ни один `components`/`definitions`
        path не утёк как report path).
      - Доп. негативные: removed endpoint (`base` содержит `/old`, `current` — нет) →
        `changes.removed == ["/old"]`; modified value under `paths` → попадает в
        `modified[ep]`; identical specs → `has_changes() is False`.
- [ ] **Debugging**: `pytest tests/openapi/ -v`
- [ ] **Contract re-verification**: используются **только** реальные deepdiff-категории
      (`dictionary_item_added`/`_removed`/`values_changed`/`type_changes`); `added`/`removed`/`modified`
      отсортированы для детерминизма; пути под `components`/`definitions` не эмитятся как endpoints.
- [ ] **Facade**: в `swax/openapi/__init__.py` добавить импорты `from .diff_specs import diff_specs`,
      `from .classify_endpoint_changes import classify_endpoint_changes`,
      `from .endpoint_diff import EndpointDiff` и расширить `__all__` (теперь 8 имён:
      `SpecParseError`, `discover_specs`, `extract_paths`, `extract_schemas`,
      `parse_spec`, `diff_specs`, `classify_endpoint_changes`, `EndpointDiff`).
- [ ] Verify facade: `python -c "from swax.openapi import diff_specs, classify_endpoint_changes, EndpointDiff"`
- [ ] Lint: `ruff check swax/openapi tests/openapi`

---

### Task 3: `swax/traceability/` — `TraceabilityGraphMissingError` + `find_affected_endpoints` + facade

Две новые сущности в import-free клетке (нет cross-cell `Imports`). Ошибка
владельцем имеет `run_plan` (не `load_traceability`); обход графа — read-only
обратная достижимость.

**Usages relevant to this task:**
- `conventions`: relative imports (`from .traceability_graph import TraceabilityGraph`
  для type hint — intra-cell, как в существующем `storage.py`), keyword-only
  Exception-класс, Google-style docstrings, `__all__`.

**Контрактные сущности (см. `swax/traceability/CODEMANIFEST`):**
- `find_affected_endpoints(changed_paths: list[str], graph: TraceabilityGraph) -> affected: list[str]`
  — `find_affected_endpoints.py`
- `TraceabilityGraphMissingError(path: pathlib.Path)` — `errors.py`

**Алгоритмы (перенесены verbatim из design-doc §`find_affected_endpoints` и контракта):**

`find_affected_endpoints`:
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
Constraint: read-only (не мутирует `graph.edges`); не импортирует из `openapi`
(принимает plain path strings); нет внутреннего cap (полное замыкание; caller
триммит перед LLM).

`TraceabilityGraphMissingError`: keyword-only `Exception`-подкласс, хранит
`path: pathlib.Path` как публичный атрибут (зеркало остальных доменных ошибок).

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/traceability/test_affected_and_error_contract.py`):
      `from swax.traceability import find_affected_endpoints, TraceabilityGraphMissingError`
      успешен; сигнатуры через `inspect` соответствуют; ошибка конструируется через
      `TraceabilityGraphMissingError(path=...)` и хранит `.path`.
- [ ] **Code**: создать `swax/traceability/errors.py`
      (`TraceabilityGraphMissingError`, keyword-only `__init__(self, *, path)`,
      `__all__ = ["TraceabilityGraphMissingError"]`); `swax/traceability/find_affected_endpoints.py`
      (routine по алгоритму выше, `from .traceability_graph import TraceabilityGraph`,
      `__all__ = ["find_affected_endpoints"]`).
- [ ] **Interface verification**: `pytest tests/traceability/test_affected_and_error_contract.py -v`
- [ ] **Logic tests** (`tests/traceability/test_affected_and_error_logic.py`) — verbatim из design-doc:
      - `test_find_affected_endpoints_reverse_reachability`:
        `TraceabilityGraph(edges={"/a": ["/b"], "/b": ["/c"], "/d": ["/c"]})`;
        `find_affected_endpoints(["/c"], graph) == ["/a", "/b", "/c", "/d"]`.
      - `test_find_affected_endpoints_keeps_changed_path_not_in_graph`:
        `TraceabilityGraph(edges={"/a": ["/b"]})`;
        `find_affected_endpoints(["/zzz"], graph) == ["/zzz"]`.
      - Доп.: `TraceabilityGraphMissingError(path=Path("x")).path == Path("x")`;
        read-only — `find_affected_endpoints` не меняет `graph.edges` после вызова.
- [ ] **Debugging**: `pytest tests/traceability/ -v`
- [ ] **Contract re-verification**: read-only; cell остаётся без cross-cell imports;
      полный affected-set без cap.
- [ ] **Facade**: в `swax/traceability/__init__.py` добавить импорты
      `from .errors import TraceabilityGraphMissingError`,
      `from .find_affected_endpoints import find_affected_endpoints` и расширить
      `__all__` (теперь 5 имён: `TraceabilityGraph`, `load_traceability`,
      `save_traceability`, `find_affected_endpoints`, `TraceabilityGraphMissingError`).
- [ ] Verify facade: `python -c "from swax.traceability import find_affected_endpoints, TraceabilityGraphMissingError"`
- [ ] Lint: `ruff check swax/traceability tests/traceability`

---

### Task 4: `swax/prompts/` — impact-report builders + facade

Две чистые routine-функции в import-free клетке. Системный промпт — константа
(роль, JSON-контракт, `risk ∈ {HIGH,MEDIUM,LOW}`, «JSON only»); пользовательский —
рендер пяти примитивов через `json.dumps`.

**Usages relevant to this task:**
- `conventions`: deterministic output (caller передаёт sorted), no paths/secrets/tokens,
  relative imports, `json.dumps` (stdlib), Google-style docstrings, `__all__`.

**Контрактные сущности (см. `swax/prompts/CODEMANIFEST`):**
- `build_impact_report_system_prompt() -> prompt: str` — `build_impact_report_system_prompt.py`
- `build_impact_report_user_prompt(added, removed, modified, affected, graph_context) -> prompt: str`
  — `build_impact_report_user_prompt.py`

**Алгоритмы (перенесены verbatim из design-doc §`build_impact_report_*`):**

`build_impact_report_system_prompt`: вернуть строковый литерал, фиксирующий:
(a) роль — «You are an API change impact analyst.»; (b) задачу — assess the
testing impact of the provided API endpoint changes; (c) JSON output contract с
ровно шестью ключами и их типами (`summary: str`, `risk: str`,
`modified/affected/requirements/checklist: list[str]`); (d) `risk ∈ {HIGH, MEDIUM, LOW}`;
(e) «JSON only — no prose, no code fences.» Без параметров, без встроенных данных.

`build_impact_report_user_prompt`:
```
1. added_json     = json.dumps(added)
   removed_json   = json.dumps(removed)
   modified_json  = json.dumps(modified, sort_keys=True)
   affected_json  = json.dumps(affected)
   graph_json     = json.dumps(graph_context, sort_keys=True)
2. Return a template string embedding the five JSON blocks and the instruction
   to return the Impact Report JSON contract from the system prompt.
```
Constraint: без silent truncation (caller триммит); без paths/tokens/secrets.

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/prompts/test_impact_report_prompts_contract.py`):
      `from swax.prompts import build_impact_report_system_prompt, build_impact_report_user_prompt`
      успешен; `build_impact_report_system_prompt()` — без параметров; сигнатура
      user-prompt через `inspect` соответствует 5 параметрам.
- [ ] **Code**: создать `swax/prompts/build_impact_report_system_prompt.py` и
      `swax/prompts/build_impact_report_user_prompt.py` (последний — `import json`,
      рендер пяти блоков). Каждый модуль — `__all__` + docstring.
- [ ] **Interface verification**: `pytest tests/prompts/test_impact_report_prompts_contract.py -v`
- [ ] **Logic tests** (`tests/prompts/test_impact_report_prompts_logic.py`):
      - system prompt содержит маркеры контракта: "impact analyst", "summary",
        "risk", "modified", "affected", "requirements", "checklist", "HIGH",
        "MEDIUM", "LOW", и запрет prose ("JSON only" или "no prose").
      - `build_impact_report_user_prompt(["/x"], [], {"/y": ["resp 200 changed"]}, ["/z"], {"/z": ["/w"]})`
        содержит `/x`, `/y`, `/z`, `/w` (все данные попали в prompt).
      - deterministic: одинаковый input → идентичная строка; `sort_keys=True` для
        `modified`/`graph_context`.
      - negative: в выводе нет маркеров secrets/paths beyond переданных данных
        (напр., нет `SWAX_LLM_TOKEN`).
- [ ] **Debugging**: `pytest tests/prompts/ -v`
- [ ] **Contract re-verification**: нет filesystem paths/tokens/secrets сверх
      переданных аргументов; без silent truncation.
- [ ] **Facade**: в `swax/prompts/__init__.py` добавить импорты
      `from .build_impact_report_system_prompt import build_impact_report_system_prompt`,
      `from .build_impact_report_user_prompt import build_impact_report_user_prompt`
      и расширить `__all__` (теперь 5 имён).
- [ ] Verify facade: `python -c "from swax.prompts import build_impact_report_system_prompt, build_impact_report_user_prompt"`
- [ ] Lint: `ruff check swax/prompts tests/prompts`

---

### Task 5: `swax/applications/plan/` — `ImpactReport` + `render_impact_report`

Фундамент use-case-клетки: pydantic-модель LLM-вывода и чистая Markdown-трансформация.
Не имеют внешних runtime-зависимостей (`ImpactReport` — pydantic; `render_impact_report`
— чистая функция), поэтому реализуются до `run_plan`.

**Usages relevant to this task:**
- `conventions`: pydantic `kw_only=True`, pure function (no I/O / LLM), Google-style
  docstrings, `__all__`.

**Контрактные сущности (см. design-doc §`ImpactReport` / §`render_impact_report`):**
- `ImpactReport(summary, risk, modified, affected, requirements, checklist)` —
  `impact_report.py`, pydantic `kw_only=True`, 6 полей (`summary: str`, `risk: str`,
  `modified: list[str]`, `affected: list[str]`, `requirements: list[str]`,
  `checklist: list[str]`), без методов.
- `render_impact_report(report: ImpactReport) -> markdown: str` — `render_impact_report.py`

**Алгоритм `render_impact_report` (перенесён verbatim из design-doc):**
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
Edge case: no-change report рендерится идентично любому другому (Summary
"No changes detected", Risk LOW, четыре пустые секции — "(none)").

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/applications/plan/test_models_and_render_contract.py`):
      `from swax.applications.plan.impact_report import ImpactReport` и
      `from swax.applications.plan.render_impact_report import render_impact_report`
      успешны; `ImpactReport` `kw_only` (`TypeError` на позиционные); `render_impact_report`
      принимает `ImpactReport` и возвращает `str`.
- [ ] **Code**: создать `swax/applications/plan/__init__.py` (пока НЕ экспортирует
      `run_plan` — он появится в Task 6; на этом шаге допустим пустой `__all__ = []`
      либо временно не трогать, если клетка ещё не импортируется; создать каталог с
      `__init__.py`), `swax/applications/plan/impact_report.py` (pydantic-модель),
      `swax/applications/plan/render_impact_report.py` (чистая трансформация).
- [ ] **Interface verification**: `pytest tests/applications/plan/test_models_and_render_contract.py -v`
- [ ] **Logic tests** (`tests/applications/plan/test_models_and_render_logic.py`) — verbatim
      design-doc edge-case test `test_render_impact_report_no_change_renders_consistently`:
      `ImpactReport(summary="No changes detected", risk="LOW", modified=[], affected=[], requirements=[], checklist=[])`;
      `md = render_impact_report(report)`; assert `"No changes detected" in md`,
      `"LOW" in md`, `"(none)" in md` (пустые секции рендерятся явно).
      Доп.: непустой report — каждая секция содержит bullet-список; `checklist` →
      `- [ ]`-элементы; deterministic (повторный вызов → идентичная строка с trailing newline).
- [ ] **Debugging**: `pytest tests/applications/plan/ -v`
- [ ] **Contract re-verification**: pure (нет I/O/LLM); нет синтезированного
      контента; `kw_only=True`.
- [ ] **Lint**: `ruff check swax/applications/plan tests/applications/plan`

---

### Task 6: `swax/applications/plan/` — `run_plan` orchestrator + `__init__` + `applications` facade

Главный use-case: 10-шаговый single-turn LLM-сценарий по образцу `run_discover`.
Defensive JSON-parse (`_parse_impact_report` — зеркало `_parse_llm_json`),
risk fallback MEDIUM, context-trimming `_MAX_AFFECTED=100`. Зависит от всех трёх
листьевых клеток (openapi diff, traceability affected, prompts). После реализации —
`run_plan` экспортируется из `applications/plan/__init__.py`, а фасад
`swax/applications` дополняется `run_plan_handler`.

**Usages relevant to this task:**
- `project-config`, `environment` (from `swax/config`): `load_config`, `Config`,
  `require_vars`.
- `specs-repository` (from `swax/git`): `clone_specs` ctx-mgr,
  `RepositoryCloneError`, `SpecsNotFoundError`.
- `parsing`, `diff` (from `swax/openapi`): `discover_specs`, `parse_spec`,
  `diff_specs`, `classify_endpoint_changes`, `EndpointDiff`.
- `graph-lifecycle`, `affected-endpoints` (from `swax/traceability`):
  `load_traceability`, `TraceabilityGraph`, `find_affected_endpoints`,
  `TraceabilityGraphMissingError`.
- `impact-report-prompts` (from `swax/prompts`): два builder-а.
- `llm-transport` (from `swax/llm`): `build_llm_client`, `LLMClient.ask`,
  `LLMResponseParseError` (и пропагируемые `LLMCallError` / `LLMRateLimitedError` /
  `UnsupportedLLMProtocolError`).
- inline `json`: `json.loads`, `json.JSONDecodeError` → `LLMResponseParseError`.
- `conventions`: `mocker.patch` на `build_llm_client` / `clone_specs` в точке
  импорта, `tmp_path`, structured logging (`logging.getLogger(__name__)`).

**Контрактные сущности (см. design-doc §`run_plan`):**
- `run_plan(project_root: pathlib.Path) -> markdown: str` — `run_plan.py`

**Внутренние helper-ы (в `run_plan.py`, вне контракта; перенесены verbatim из design-doc):**

`_parse_spec_map(paths, root) -> dict[str, dict]`:
```
{p.relative_to(root).as_posix(): parse_spec(p) for p in paths}
```

`_diff_and_classify(baseline, fresh) -> EndpointDiff`:
```
for rel in the union of keys:
  both sides:  raw = diff_specs(baseline[rel], fresh[rel])
               pair = classify_endpoint_changes(raw)
               merge pair.added/removed/modified into the running aggregate
  fresh-only:  added.extend(sorted(fresh[rel].get("paths", {}).keys()))
               # diffing against {} does NOT surface individual endpoints
               # (deepdiff reports the top-level `paths` key) → read paths directly
  baseline-only: removed.extend(sorted(baseline[rel].get("paths", {}).keys()))
merge dedups added/removed; extends modified[ep]. Return the aggregate.
```

`_build_graph_context(affected, changed, graph) -> tuple[dict[str, list[str]], list[str]]`:
```
_MAX_AFFECTED = 100
if len(affected) > _MAX_AFFECTED:
    kept = (changed first, in their existing order) + sorted(remainder), truncated to _MAX_AFFECTED
    logger.warning("plan context truncated", extra={"affected": len(affected), "kept": _MAX_AFFECTED})
else:
    kept = affected
return ({p: list(graph.edges.get(p, [])) for p in kept}, sorted(kept))
```

`_parse_impact_report(raw) -> ImpactReport` (зеркало `_parse_llm_json`):
```
stripped = _strip_prose_and_fences(raw)   # first-{ to last-} slice (reuse discover helper convention)
try:
    parsed = json.loads(stripped)
except json.JSONDecodeError as exc:
    raise LLMResponseParseError(reason=str(exc), excerpt=raw[:200]) from exc
validate parsed is a dict with exactly the six keys
validate value types (summary: str, risk: str, modified/affected/requirements/checklist: list[str])
risk = parsed["risk"].upper()
if risk not in {"HIGH", "MEDIUM", "LOW"}:
    risk = "MEDIUM"; logger.warning("invalid risk, falling back to MEDIUM", extra={"risk": parsed["risk"]})
return ImpactReport(summary=..., risk=risk, modified=..., affected=..., requirements=..., checklist=...)
on any shape mismatch → raise LLMResponseParseError(reason=..., excerpt=raw[:200])
```

**Алгоритм `run_plan` (перенесён verbatim из design-doc §`run_plan`):**
```
1. require_vars()                                  # MissingEnvironmentVariablesError propagates
   logger.info("plan started", extra={"project_root": str(project_root)})

2. config = load_config(project_root / ".swax" / "config.yml")

3. traceability_path = project_root / ".swax" / "traceability.yml"
   if not traceability_path.exists():
     raise TraceabilityGraphMissingError(path=traceability_path)
   graph = load_traceability(traceability_path)

4. baseline_root = project_root / config.specs.location
   baseline = _parse_spec_map(discover_specs(baseline_root), baseline_root)
   with clone_specs(config.git.url, config.git.location) as fresh_root:   # RepositoryCloneError / SpecsNotFoundError propagate
       fresh = _parse_spec_map(discover_specs(fresh_root), fresh_root)
       merged = _diff_and_classify(baseline, fresh)                       # one EndpointDiff across matching pairs
   # NOTE: parse_spec inside _parse_spec_map may raise SpecParseError (propagates).
   # The clone ctx-mgr ensures temp-dir cleanup on every outcome.

5. if not merged.has_changes():
       report = ImpactReport(
           summary="No changes detected", risk="LOW",
           modified=[], affected=[], requirements=[], checklist=[])
       logger.info("plan completed: no changes")
       return render_impact_report(report)

6. changed = merged.changed_paths()
   affected = find_affected_endpoints(changed, graph)
   graph_context, trimmed_affected = _build_graph_context(affected, changed, graph)
   system = build_impact_report_system_prompt()
   user = build_impact_report_user_prompt(
       added=merged.added, removed=merged.removed, modified=merged.modified,
       affected=trimmed_affected, graph_context=graph_context)

7. client = build_llm_client()                                            # UnsupportedLLMProtocolError propagates
   raw = client.ask(system=system, user=user)                             # LLMCallError / LLMRateLimitedError propagate
   report = _parse_impact_report(raw)                                     # LLMResponseParseError on bad JSON/shape

8. logger.info("plan completed", extra={"changed": len(changed), "affected": len(affected)})
   return render_impact_report(report)
```

**Errors propagated (без catch):** `MissingEnvironmentVariablesError`,
`SpecParseError`, `LLMCallError`, `LLMRateLimitedError`,
`UnsupportedLLMProtocolError`, `LLMResponseParseError`,
`RepositoryCloneError`, `SpecsNotFoundError`, `TraceabilityGraphMissingError`.

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/applications/plan/test_run_plan_contract.py`):
      `from swax.applications.plan import run_plan` успешен; сигнатура через
      `inspect.signature(run_plan)` == `(project_root: pathlib.Path)` с аннотацией
      возврата `str`.
- [ ] **Code**: создать `swax/applications/plan/run_plan.py` с `run_plan` + 4
      приватными helper-ами (`_parse_spec_map`, `_diff_and_classify`,
      `_build_graph_context`, `_parse_impact_report`, и переиспользовать/локально
      определить `_strip_prose_and_fences` по образцу `run_discover`). Cross-cell
      импорты абсолютные (`from ...config import Config, load_config, require_vars`,
      `from ...git import clone_specs`, `from ...openapi import ...`,
      `from ...traceability import ...`, `from ...prompts import ...`,
      `from ...llm import LLMClient, LLMResponseParseError, build_llm_client`).
      Внутриклеточные — relative (`from .impact_report import ImpactReport`,
      `from .render_impact_report import render_impact_report`). `_MAX_AFFECTED = 100`
      как module-level константа. `logger = logging.getLogger(__name__)`.
      Module-level `__all__: list[str] = ["run_plan"]`.
- [ ] **Interface verification**: `pytest tests/applications/plan/test_run_plan_contract.py -v`
- [ ] **Logic tests** (`tests/applications/plan/test_run_plan_logic.py`) — verbatim из
      design-doc Test Stack Trace (mock на `build_llm_client` и `clone_specs` в точке
      импорта; `tmp_path` проект с `.swax/config.yml`, `.swax/traceability.yml`,
      baseline specs):
      - `test_run_plan_no_changes_skips_llm_and_returns_low_risk` (positive):
        fresh spec идентичен baseline; assert `"No changes detected" in markdown`,
        `"LOW" in markdown`, `mock_build_llm_client.assert_not_called()`.
      - `test_run_plan_raises_missing_graph_when_traceability_absent` (negative):
        `.swax/traceability.yml` отсутствует → `pytest.raises(TraceabilityGraphMissingError)`,
        `exc.value.path.name == "traceability.yml"`.
      - `test_run_plan_invalid_risk_falls_back_to_medium` (negative): fresh spec
        добавляет эндпоинт; mock `ask` возвращает JSON с `"risk": "EXTREME"` →
        `"MEDIUM" in markdown`, `"EXTREME" not in markdown`, `caplog` WARNING содержит "risk".
      - `test_run_plan_propagates_llm_response_parse_error_on_bad_json` (negative):
        `ask` возвращает `"not json at all"` → `pytest.raises(LLMResponseParseError)`.
      - Доп.: `test_run_plan_propagates_repository_clone_error`,
        `test_run_plan_propagates_specs_not_found` — `clone_specs.side_effect` поднимает
        соответствующую ошибку → пробрасывается без catch.
      - Доп.: one-sided spec (`fresh-only` → `added` из `paths`; `baseline-only` →
        `removed`) — покрывает ветви `_diff_and_classify` (напрямую чтение `paths`,
        не diff против `{}`).
- [ ] **Debugging**: `pytest tests/applications/plan/ -v`
- [ ] **Contract re-verification**: paths only в отчёте; defensive parsing активен
      (risk fallback); `SWAX_LLM_TOKEN` не в логах/Markdown; cleanup клона на любом исходе;
      `run_plan` поднимает `TraceabilityGraphMissingError` сам (existence check до `load_traceability`).
- [ ] **Facade (sub-cell)**: в `swax/applications/plan/__init__.py` добавить
      `from .run_plan import run_plan` и `__all__: list[str] = ["run_plan"]`
      (docstring клетки — по образцу `swax/applications/discover/__init__.py`).
- [ ] **Facade (aggregator)**: в `swax/applications/__init__.py` добавить
      `from .plan import run_plan as run_plan_handler` и расширить `__all__`
      (теперь 3 имени: `run_discover_handler`, `run_init_handler`, `run_plan_handler`).
      Обновить module docstring (упомянуть третий re-export).
- [ ] **Facade test**: создать `tests/applications/test_applications_facade.py` по
      образцу `tests/commands/test_commands_facade.py` — assert `run_plan_handler`,
      `run_init_handler`, `run_discover_handler` импортируемы; callable;
      `__all__ == ["run_discover_handler", "run_init_handler", "run_plan_handler"]`;
      `run_plan_handler is run_plan`.
- [ ] Verify facade: `python -c "from swax.applications import run_plan_handler, run_init_handler, run_discover_handler; assert callable(run_plan_handler)"`
- [ ] Lint: `ruff check swax/applications tests/applications`

---

### Task 7: `swax/commands/plan/` — `plan` handler + `__init__` + `commands` facade

Тонкий Click-обработчик: delegate → echo → map 9 доменных ошибок. Строго по образцу
`swax/commands/discover/discover.py` (`TYPE_CHECKING` для `SwaxContext`, чтобы не
ввести цикл `cli ↔ commands`; `from __future__ import annotations`). После
реализации — фасад `swax/commands` дополняется `plan_handler` (что и замыкает
импорт `plan_handler` в уже обновлённом `swax/cli/__main__.py`).

**Usages relevant to this task:**
- `click`: `@click.command()`, `@click.pass_obj`, `click.echo`, `click.ClickException`,
  `click.testing.CliRunner`.
- `cli-facade` (from `swax/cli`): паттерн доступа `SwaxContext` (TYPE_CHECKING only).
- `plan-usage` (from `swax/applications`): `run_plan` semantics (`run_plan_handler`).
- `environment`, `parsing`, `llm-transport`, `specs-repository`, `affected-endpoints`:
  доменные error-типы для маппинга (9 шт.).
- `conventions`: `mocker.patch` на `swax.commands.plan.plan.run_plan`, `CliRunner.invoke`.

**Контрактные сущности (см. design-doc §`plan` handler):**
- `plan(ctx: SwaxContext)` — `plan.py` (Click command)

**Алгоритм `plan` (перенесён verbatim из design-doc §`plan`):**
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
Импорты: `from ...applications import run_plan_handler as run_plan`; доменные
ошибки напрямую из `swax.config`, `swax.openapi`, `swax.git`, `swax.traceability`,
`swax.llm` (absolute cross-cell); `SwaxContext` под `TYPE_CHECKING`
(`from ...cli import SwaxContext`). Generic `Exception` никогда не ловится;
`SWAX_LLM_TOKEN` не попадает ни в одно сообщение.

**CRITICAL: `CODEMANIFEST` — read-only контракт. Не модифицировать.**

- [ ] **Contract tests** (`tests/commands/plan/test_plan_contract.py`):
      `from swax.commands.plan import plan` успешен; `isinstance(plan, click.Command)`;
      callback decorated с `@click.pass_obj` (через `plan.params` / callback-инспекцию).
- [ ] **Code**: создать `swax/commands/plan/__init__.py` (`from .plan import plan`,
      `__all__: list[str] = ["plan"]`, docstring по образцу `swax/commands/discover/__init__.py`);
      `swax/commands/plan/plan.py` по алгоритму выше
      (`from __future__ import annotations`, `TYPE_CHECKING` блок для `SwaxContext`,
      `@click.command()` + `@click.pass_obj`, module-level `__all__: list[str] = ["plan"]`).
- [ ] **Interface verification**: `pytest tests/commands/plan/test_plan_contract.py -v`
- [ ] **Logic tests** (`tests/commands/plan/test_plan_logic.py`) — verbatim из design-doc
      Test Stack Trace (mock `run_plan` в точке импорта `swax.commands.plan.plan.run_plan`;
      `CliRunner().invoke(main, ["plan"])`):
      - `test_plan_handler_echoes_markdown_and_maps_missing_graph` (positive + edge):
        case a — `run_plan` возвращает `"# Impact Report ..."` → `exit_code == 0`,
        `"# Impact Report" in result.output`; case b — `run_plan` поднимает
        `TraceabilityGraphMissingError(path=...)` → `exit_code == 1`,
        `"Traceability graph not found" in result.output` and `"swax discover" in result.output`.
      - `test_plan_handler_maps_all_nine_domain_errors` (edge, parametrize × 9):
        для каждой пары `(exception, message_fragment)` из error-таблицы →
        `exit_code == 1`, `message_fragment in result.output`,
        `"SWAX_LLM_TOKEN" not in result.output`.
      - Доп.: `test_plan_handler_no_prompts` — invoke без stdin, mock успехом →
        `exit_code == 0` (command без опций/промптов).
- [ ] **Debugging**: `pytest tests/commands/plan/ -v`
- [ ] **Contract re-verification**: маппятся ровно 9 documented exceptions; generic
      `Exception` не ловится; `SWAX_LLM_TOKEN` не в сообщениях; `SwaxContext` только
      под `TYPE_CHECKING` (цикл `cli ↔ commands` не введён).
- [ ] **Facade (aggregator)**: в `swax/commands/__init__.py` добавить
      `from .plan import plan as plan_handler` и расширить `__all__`
      (теперь 3 имени: `discover_handler`, `init_handler`, `plan_handler`).
      Обновить module docstring (упомянуть третий re-export).
- [ ] **Facade test**: расширить `tests/commands/test_commands_facade.py` — добавить
      `plan_handler` в импорты; assert `isinstance(plan_handler, click.Command)`;
      `__all__ == ["discover_handler", "init_handler", "plan_handler"]`;
      `plan_handler is plan` (из `swax.commands.plan`).
- [ ] Verify facade: `python -c "from swax.commands import plan_handler; import click; assert isinstance(plan_handler, click.Command)"`
- [ ] Verify end-to-end import (это замыкает `__main__.py`): `python -c "from swax.cli.__main__ import main; assert 'plan' in main.commands"`
- [ ] Lint: `ruff check swax/commands tests/commands`

---

### Task 8: Integration tests — end-to-end `swax plan`

Сквозной сценарий через `CliRunner` с замокированными `clone_specs` и LLM.
Подтверждает, что `main → plan → run_plan → render → echo` работает целиком и
регистрация `plan` на группе `main` активна.

**Usages relevant to this task:**
- `click`: `CliRunner`.
- `conventions`: `tmp_path` проект, `monkeypatch.setenv` для `SWAX_LLM_*`,
  `mocker.patch` на `build_llm_client` и `clone_specs` в точке импорта.
- Все cell-level usages, упомянутые в design-doc.

- [ ] Создать `tests/integration/test_plan.py` (с `tests/integration/__init__.py`
      уже существует).
- [ ] `test_swax_plan_end_to_end_with_mocked_llm` — `tmp_path` с `.swax/config.yml`,
      `.swax/traceability.yml` (минимальный граф `/a -> /b`), baseline spec под
      `tmp_path/<specs.location>`; `mocker.patch("swax.applications.plan.run_plan.clone_specs")`
      yields fresh root с **изменённой** spec (один добавленный/изменённый эндпоинт);
      `mocker.patch("swax.applications.plan.run_plan.build_llm_client")` returns mock,
      `ask` возвращает валидный 6-ключевой JSON; `monkeypatch.setenv` SWAX_LLM_*;
      `CliRunner().invoke(main, ["--env-file", ".env", "plan"])` → asserts `exit_code == 0`,
      `"# Impact Report" in result.output`, `"Summary:" in result.output`.
- [ ] `test_swax_plan_no_changes_short_circuits` — fresh spec идентичен baseline →
      `exit_code == 0`, `"No changes detected" in result.output`,
      `mock_build_llm_client.assert_not_called()`.
- [ ] `test_swax_plan_missing_traceability_maps_to_hint` — `.swax/traceability.yml`
      отсутствует → `exit_code == 1`, `"Traceability graph not found" in result.output`,
      `"swax discover" in result.output`.
- [ ] Run validation: `pytest tests/integration/test_plan.py -v`

---

## Validation Commands

- `pytest tests/ -v`: запустить все тесты проекта.
- `pytest tests/<cell>/ -v`: запустить тесты одной клетки
  (`tests/openapi`, `tests/traceability`, `tests/prompts`,
  `tests/applications/plan`, `tests/commands/plan`, `tests/integration`).
- `ruff check swax tests`: линтер (включая `E`, `W`, `F`, `I`, `N`, `UP`, `B`,
  `SIM`, `PL`, `PLR`, `C4`, `DTZ`, `PT`, `ARG`, `RUF`, `PTH`, `C90` — см.
  `pyproject.toml`; `max-complexity = 10`).
- `ruff format --check swax tests`: проверка форматирования.
- Facade smoke (per cell):
  - `python -c "from swax.openapi import diff_specs, classify_endpoint_changes, EndpointDiff"`
  - `python -c "from swax.traceability import find_affected_endpoints, TraceabilityGraphMissingError"`
  - `python -c "from swax.prompts import build_impact_report_system_prompt, build_impact_report_user_prompt"`
  - `python -c "from swax.applications.plan import run_plan"`
  - `python -c "from swax.applications import run_plan_handler"`
  - `python -c "from swax.commands.plan import plan"`
  - `python -c "from swax.commands import plan_handler"`
- End-to-end import (замыкает `__main__.py`):
  `python -c "from swax.cli.__main__ import main; assert set(main.commands) >= {'init','discover','plan'}"`.
- CLI entry point (mocked LLM):
  - `swax --env-file .env plan` печатает Markdown Impact Report.
  - `swax plan` без `.swax/traceability.yml` → exit 1, сообщение со `swax discover`.

---

## Completion Criteria

- [ ] Каждое новое контрактное entity реализовано в правильном `location`
      (`diff_specs.py`, `classify_endpoint_changes.py`, `endpoint_diff.py`,
      `find_affected_endpoints.py`, `errors.py` (traceability),
      `build_impact_report_system_prompt.py`, `build_impact_report_user_prompt.py`,
      `run_plan.py`, `impact_report.py`, `render_impact_report.py`,
      `swax/applications/plan/__init__.py`, `plan.py`, `swax/commands/plan/__init__.py`).
- [ ] Каждое новое entity доступно из фасада своей клетки (`__init__.py.__all__`):
      `openapi` (8 имён), `traceability` (5 имён), `prompts` (5 имён),
      `applications/plan` (`run_plan`), `commands/plan` (`plan`).
- [ ] Агрегирующие фасады `swax/applications` (`run_plan_handler`) и
      `swax/commands` (`plan_handler`) расширены; `swax/cli/__main__.py` не
      изменялся (уже регистрирует `plan`).
- [x] Свойства и методы (`EndpointDiff.has_changes` / `changed_paths`) соответствуют
      объявленным сигнатурам.
- [ ] Алгоритмы/Algorithm-ы отражены в поведении (verified логическими тестами,
      verbatim из design-doc Test Stack Trace).
- [ ] Контрактные cross-cell зависимости разрешены: импорты `run_plan` из шести
      provider-клеток работают; цикл `cli ↔ commands` не введён (`SwaxContext`
      под `TYPE_CHECKING`).
- [ ] Re-exports `run_plan_handler`, `plan_handler` доступны из соответствующих
      фасадов; `swax plan` регистрируется без `ImportError`.
- [ ] Каждая coding-задача прошла TDD-цикл (контракт-тесты → код → interface
      verification → logic-тесты → debugging → re-verification → lint).
- [ ] Контракт-тесты и logic-тесты покрывают фасад, API и поведение в каждой
      coding-задаче; все 9 доменных ошибок маппятся в `plan` handler.
- [ ] Интеграционный тест покрывает end-to-end `swax plan` (mocked clone + LLM).
- [ ] Ни одна граница клетки не была расширена — новые клетки не создавались
      (`swax/applications/plan` и `swax/commands/plan` уже материализованы
      стадией `apply-architecture`).
- [ ] `CODEMANIFEST` файлы и `.usages/` не модифицировались (read-only).
- [x] `deepdiff>=8.0` добавлен в `pyproject.toml`.
- [ ] Все команды валидации проходят (`pytest tests/ -x`, `ruff check swax/`).
- [ ] Каждое Usages-указание упомянуто минимум в одной задаче (`conventions`,
      `deepdiff`, `click`, шесть imported usages provider-клеток, inline `json`).
