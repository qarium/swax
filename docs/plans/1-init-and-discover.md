# Plan: `1-init-and-discover`

## Purpose

Greenfield-реализация фундамента CLI Swax. После выполнения плана проект предоставляет:
- две CLI-команды (`swax init`, `swax discover`) поверх Click, зарегистрированные в `swax.cli.__main__:main`;
- доменные клетки `config`, `fs`, `git`, `openapi`, `traceability`, `prompts`, `llm` со сквозной моделью ошибок;
- use-case-слой `applications/{init,discover}` и тонкие command-обработчики `commands/{init,discover}`;
- две фасадные клетки-агрегаторы (`applications`, `commands`) и точку входа `cli` со `SwaxContext`.

Стратегия реализации — bottom-up: листья → `llm` + use-cases → facades → handlers → `cli`. В каждой coding-задаче сначала пишутся контракт-тесты (фасад, сигнатуры), затем код, затем логические тесты. `CODEMANIFEST`-файлы и `.usages/` уже материализованы и считаются **read-only**.

## Context

### Contract Surface

(Все 14 контрактов уже материализованы. Ниже — краткий per-cell список сущностей с `location` и фасадными обязательствами. Полные сигнатуры и алгоритмы см. в соответствующем `CODEMANIFEST` и в `docs/design/1-init-and-discover.md` §Algorithm Design.)

**Cell: `swax/config/`**
- `Config(git: GitConfig, specs: SpecsConfig)` — Entity, `Config.py`, pydantic kw_only
- `GitConfig(url: str, location: str)` — Entity, `GitConfig.py`
- `SpecsConfig(type: Literal['swagger','openapi'], location: str)` — Entity, `SpecsConfig.py`
- `MissingEnvironmentVariablesError(missing: list[str])` — Entity, `errors.py`
- `InvalidLLMProtocolError(value: str, allowed: tuple[str, ...])` — Entity, `errors.py`
- `InvalidLLMBaseURLError(value: str)` — Entity, `errors.py`
- `load_env(env_file: pathlib.Path)` — Routine, `env.py`
- `require_vars() -> vars: dict[str, str]` — Routine, `env.py`
- `parse_protocol(value: str) -> protocol: str` — Routine, `env.py`
- `parse_base_url(value: str) -> base_url: str` — Routine, `env.py`
- `load_config(path: pathlib.Path) -> config: Config` — Routine, `storage.py`
- `save_config(config: Config, path: pathlib.Path)` — Routine, `storage.py`
- Фасад: все 12 имён в `swax/config/__init__.py.__all__`
- Usages: `conventions`, `pyyaml`, `python-dotenv`

**Cell: `swax/fs/`**
- `ensure_swax_dir(project_root) -> swax_dir` — Routine, `ensure_swax_dir.py`
- `copy_specs(source, destination)` — Routine, `copy_specs.py` (`shutil.copytree(dirs_exist_ok=True)`, `symlinks=False` — дефолт)
- Фасад: оба имени в `__all__`
- Usages: `conventions`

**Cell: `swax/git/`**
- `clone_specs(repo_url, specs_location) -> Iterator[pathlib.Path]` — Routine (contextmanager), `clone_specs.py`
- `RepositoryCloneError(url, reason)` — Entity, `errors.py`
- `SpecsNotFoundError(path)` — Entity, `errors.py`
- Фасад: все 3 имени в `__all__`
- Usages: `conventions`, `gitpython`

**Cell: `swax/openapi/`**
- `parse_spec(spec_path) -> dict` — Routine, `parse_spec.py` (prance `ResolvingParser`, backend `openapi-spec-validator`, `strict=False`, `resolve_types=True`)
- `extract_paths(spec) -> list[str]` — Routine, `extract_paths.py`
- `extract_schemas(spec) -> dict` — Routine, `extract_schemas.py` (OpenAPI 3.x `components.schemas` или Swagger 2.0 `definitions`)
- `discover_specs(root) -> list[pathlib.Path]` — Routine, `discover_specs.py`
- `SpecParseError(path, reason)` — Entity, `errors.py`
- Фасад: все 5 имён в `__all__`
- Usages: `conventions`, `prance`, `pyyaml`

**Cell: `swax/traceability/`**
- `TraceabilityGraph(edges: dict[str, list[str]])` — Entity, `TraceabilityGraph.py`, pydantic kw_only
  - property `edges -> dict[str, list[str]]`
  - method `add_edge(source: str, target: str)`
  - method `deduplicate()` (sorted set, removes self-loops, idempotent)
- `load_traceability(path) -> TraceabilityGraph` — Routine, `storage.py`
- `save_traceability(graph, path)` — Routine, `storage.py` (sorted в Python, deterministic YAML)
- Фасад: 3 имени в `__all__`
- Usages: `conventions`, `pyyaml`

**Cell: `swax/prompts/`**
- `build_graph_system_prompt() -> str` — Routine, `build_graph_system_prompt.py`
- `build_graph_user_prompt(endpoints: list[str]) -> str` — Routine, `build_graph_user_prompt.py` (output contract: `{dependencies, uncertain}`)
- `build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> str` — Routine, `build_refine_user_prompt.py`
- Фасад: 3 имени в `__all__`
- Usages: `conventions`

**Cell: `swax/llm/`** (Imports from `swax/config`)
- `LLMClient` — Protocol Entity, `LLMClient.py` (методы `ask`, `ask_multi_turn`)
- `LLMClient::AnthropicAdapter(client)` — Mutation Entity, `AnthropicAdapter.py`, property `client`, методы `ask`, `ask_multi_turn`
- `LLMClient::OpenAIAdapter(client)` — Mutation Entity, `OpenAIAdapter.py`, property `client`, методы `ask`, `ask_multi_turn`
- `LLMCallError(reason)`, `LLMRateLimitedError(reason)`, `LLMResponseParseError(reason, excerpt)`, `UnsupportedLLMProtocolError(protocol)` — Entities, `errors.py`
- `build_anthropic_client() -> Anthropic` — Routine, `build_anthropic_client.py`
- `build_openai_client() -> OpenAI` — Routine, `build_openai_client.py`
- `build_llm_client() -> LLMClient` — Routine, `build_llm_client.py`
- Фасад: 9 имён в `__all__`
- Usages: `conventions`, `anthropic`, `openai` + Imported Usages `environment`

**Cell: `swax/applications/init/`** (Imports from `swax/config`, `swax/git`, `swax/fs`)
- `run_init(repo_url, specs_location, download_path, project_root)` — Routine, `run_init.py`
- Фасад: `run_init` в `__all__`

**Cell: `swax/applications/discover/`** (Imports from `swax/config`, `swax/openapi`, `swax/llm`, `swax/prompts`, `swax/traceability`)
- `run_discover(project_root)` — Routine, `run_discover.py` (two-pass LLM)
- Внутренние helper-ы вне контракта: `_strip_prose_and_fences`, `_parse_llm_json(raw, *, first_pass)`, `_validate_dependency_shape(d)` (см. §Algorithm Design в design-doc)
- Фасад: `run_discover` в `__all__`
- Inline Usages: `json` (stdlib)

**Cell: `swax/applications/`** (facade, Imports from `swax/applications/{init,discover}`)
- Re-exports: `->run_init_handler`, `->run_discover_handler`
- Фасад: `run_init_handler`, `run_discover_handler` в `__all__`

**Cell: `swax/commands/init/`** (Imports from `swax/cli`, `swax/applications`, `swax/git`)
- `init(ctx: click.Context)` — Routine, `init.py`
- Фасад: `init` в `__all__`

**Cell: `swax/commands/discover/`** (Imports from `swax/cli`, `swax/applications`, `swax/config`, `swax/openapi`, `swax/llm`)
- `discover(ctx: click.Context)` — Routine, `discover.py`
- Фасад: `discover` в `__all__`

**Cell: `swax/commands/`** (facade, Imports from `swax/commands/{init,discover}`)
- Re-exports: `->init_handler`, `->discover_handler`
- Фасад: `init_handler`, `discover_handler` в `__all__`

**Cell: `swax/cli/`** (Imports from `swax/config`)
- `main(ctx, env_file)` — Routine, `main.py` (Click group, `--env-file`, `click.Path(exists=False, dir_okay=False, path_type=pathlib.Path)`)
- `SwaxContext(env_file: pathlib.Path)` — Entity, `SwaxContext.py`, pydantic kw_only
  - property `env_file -> pathlib.Path`
  - property `config -> Config | None` (default `None`)
- `__main__.py` (не контракт — lazy registration of `init`/`discover` на `main`)
- Фасад: `main`, `SwaxContext` в `__all__`

### Re-exports

| Re-export | Source | Facade |
|-----------|--------|--------|
| `run_init_handler` | `run_init AS run_init_handler` из `swax/applications/init` | `swax/applications` |
| `run_discover_handler` | `run_discover AS run_discover_handler` из `swax/applications/discover` | `swax/applications` |
| `init_handler` | `init AS init_handler` из `swax/commands/init` | `swax/commands` |
| `discover_handler` | `discover AS discover_handler` из `swax/commands/discover` | `swax/commands` |

### Usages Context

**Project-level (`.goga/usages/`)**
- `conventions` — Python code rules, pydantic kw_only, testing discipline (`tmp_path`/`monkeypatch`/`mocker`), relative imports
- `pyyaml` — `yaml.safe_load`, `yaml.safe_dump(sort_keys=False, allow_unicode=True, default_flow_style=False)`, UTF-8
- `python-dotenv` — `load_dotenv(override=False)`, REQUIRED_VARS list
- `gitpython` — `Repo.clone_from(url, tmp, depth=1)`, `GitCommandError` mapping
- `prance` — `ResolvingParser(str(path), backend="openapi-spec-validator", strict=False, resolve_types=True)`, `.specification`
- `anthropic` — `Anthropic(api_key, base_url)`, `client.messages.create(model, max_tokens, system, messages)`, `block.text`, `RateLimitError`/`APIError` mapping
- `openai` — `OpenAI(api_key, base_url)`, `client.chat.completions.create(model, messages)`, `response.choices[0].message.content or ""`, error mapping
- `click` — `@click.group`, `@click.command`, `@click.pass_context`, `@click.pass_obj`, `click.Path`, `click.prompt`, `click.ClickException`

**Inline (in `swax/applications/discover/CODEMANIFEST`)**
- `json` — stdlib; `json.loads`, catch `json.JSONDecodeError`, wrap into `LLMResponseParseError`

### Imported Usages (cell-level)

| Usage | From cell | Used in |
|-------|-----------|---------|
| `environment` | `swax/config` | `swax/cli`, `swax/llm`, `swax/commands/discover` |
| `project-config` | `swax/config` | `swax/applications/init`, `swax/applications/discover`, `swax/cli` |
| `project-layout` | `swax/fs` | `swax/applications/init` |
| `specs-repository` | `swax/git` | `swax/applications/init`, `swax/commands/init` |
| `parsing` | `swax/openapi` | `swax/applications/discover`, `swax/commands/discover` |
| `extraction` | `swax/openapi` | `swax/applications/discover` |
| `llm-transport` | `swax/llm` | `swax/applications/discover`, `swax/commands/discover` |
| `traceability-llm-prompts` | `swax/prompts` | `swax/applications/discover` |
| `graph-lifecycle` | `swax/traceability` | `swax/applications/discover` |
| `cli-facade` | `swax/cli` | `swax/commands/init`, `swax/commands/discover` |
| `init` (alias `init-usage` в `swax/commands/init`) | `swax/applications` | `swax/commands/init` |
| `discover` (alias `discover-usage` в `swax/commands/discover`) | `swax/applications` | `swax/commands/discover` |

### Local Usages

Все 12 `.usages/` файлов уже созданы и синхронизированы. В задаче 1 новых файлов не создаётся; `swax/applications/.usages/discover.md` уже отражает `LLMResponseParseError` (review pass 2).

### External Dependencies

- Сторонние: `click>=8.0`, `pydantic>=2.0`, `pyyaml>=6.0`, `gitpython>=3.1`, `prance>=23.0`, `anthropic>=0.40`, `openai>=1.50`, `python-dotenv>=1.0` (+ transitive `openapi-spec-validator`).
- Stdlib: `pathlib`, `tempfile`, `shutil`, `os`, `json`, `logging`, `typing` (`Protocol`, `Literal`, `Iterator`, `Optional`).
- Тестовые: `pytest>=8.0`, `pytest-cov>=5.0`, `pytest-mock` (требует добавления), `ruff>=0.15.0`.

## Facts

- Версия Python: `>=3.10` (`pyproject.toml`). Используется `typing.Optional` (правило `UP045` отключено — `X | None` несовместим с pydantic-полями на 3.10).
- Все pydantic-модели во всех клетках — `kw_only=True`.
- `DEFAULT_MODEL` фиксирован в коде адаптеров (не в env) — выбран актуальный anthropic/openai модельный идентификатор на момент реализации.
- `shutil.copytree` в `copy_specs` вызывается БЕЗ `symlinks=True` — symlinks копируются как regular files (default).
- `clone_specs` использует `tempfile.TemporaryDirectory(prefix="swax-")` + `Repo.clone_from(url, tmp, depth=1)`.
- `parse_spec` использует prance `ResolvingParser` с `backend="openapi-spec-validator"`.
- `click.Path(exists=False, dir_okay=False, path_type=pathlib.Path)` для `--env-file` (decision Д2).
- Команды регистрируются в `swax/cli/__main__.py`, не в `__init__.py` (разрывает цикл `cli ↔ commands`).
- Тесты всегда mock-ют SDK и LLM-вызовы (`mocker.patch` в точке импорта). Никаких live API вызовов.
- `LLMResponseParseError` объявлен в `swax/llm/errors.py` и используется в `swax/applications/discover/run_discover.py` (helper) и `swax/commands/discover/discover.py` (mapping).
- `discover` handler формально не использует поля `ctx.obj`, но импорт `SwaxContext` и usage `cli-facade` сохранены для единства API init/discover (intentional).

## Gap Analysis

- **Missing contract entities**: все — greenfield. Ни один `*.py` не существует.
- **Missing facade exposure**: `__init__.py` отсутствует во всех 14 клетках.
- **`location` placement**: каждое `*.py` имя из контракта должно быть создано на уровне каталога клетки.
- **Тестовый слой**: каталог `tests/` не существует; `pytest-mock` не в зависимостях.
- **Зависимости `pyproject.toml`**: `[project].dependencies` пуст — заполнить перед запуском тестов.
- **`pyproject.toml [project.scripts]`**: отсутствует — добавить `swax = "swax.cli.__main__:main"`.
- **CLI entry `swax/cli/__main__.py`**: не описан как контракт, но обязательная часть архитектуры (lazy registration).

---

## Tasks

> **Package ordering rule**: задачи выполняются строго в порядке листьев → корень (см. таблицу ниже). Внутри coding-задачи — TDD: контракт-тесты → код → interface verification → logic-тесты → debugging → contract re-verification → lint.

> **CRITICAL для всех задач**: `CODEMANIFEST` и `.usages/` — **read-only**. Если реализация не сходится с контрактом, фиксируйте реализацию, не контракт.

### Порядок выполнения

| # | Cell | Уровень |
|---|------|---------|
| 1 | `swax/config/` | 0 (leaf) |
| 2 | `swax/fs/` | 0 (leaf) |
| 3 | `swax/git/` | 0 (leaf) |
| 4 | `swax/openapi/` | 0 (leaf) |
| 5 | `swax/traceability/` | 0 (leaf) |
| 6 | `swax/prompts/` | 0 (leaf) |
| 7 | `swax/llm/` | 1 |
| 8 | `swax/applications/init/` | 1 |
| 9 | `swax/applications/discover/` | 1 |
| 10 | `swax/applications/` (facade) | 2 |
| 11 | `swax/commands/init/` | 2 |
| 12 | `swax/commands/discover/` | 2 |
| 13 | `swax/commands/` (facade) | 2 |
| 14 | `swax/cli/` | 3 |

---

### Task 0: Project bootstrap (infrastructure)

Подготовка `pyproject.toml` и тестового каркаса до первого coding-теста. Без этого шаги верификации невозможны.

**Usages relevant to this task:**
- `conventions`: тестовый слой `tests/` зеркалит `swax/`, `tmp_path`/`monkeypatch`/`mocker` fixtures; для `mocker` требуется `pytest-mock`.

- [x] В `[project].dependencies` добавить: `click>=8.0`, `pydantic>=2.0`, `pyyaml>=6.0`, `gitpython>=3.1`, `prance>=23.0`, `anthropic>=0.40`, `openai>=1.50`, `python-dotenv>=1.0`
- [x] В `[project.optional-dependencies].test` добавить `pytest-mock>=3.10`
- [x] Добавить секцию `[project.scripts]` с записью `swax = "swax.cli.__main__:main"`
- [x] Создать `tests/__init__.py` и `tests/conftest.py` (пустые, для shared fixtures позже)
- [x] Установить пакет в editable-режиме с тестовыми зависимостями: `pip install -e '.[test]'`
- [x] Smoke: `python -c "import swax"` пока падает — это ожидаемо (пакет пуст), фиксится последующими задачами

---

### Task 1: `swax/config/` cell skeleton (infrastructure)

Создать Python-пакет `swax/config/` с пустым фасадом `__init__.py` (`__all__ = []` на этом шаге), `errors.py` (только объявления исключений), чтобы следующие coding-задачи могли добавлять модули. Реализация сущностей — в задачах 2–6.

**Usages relevant to this task:**
- `conventions`: relative imports внутри клетки, pydantic kw_only.

- [x] Создать `swax/config/__init__.py` (пока `__all__: list[str] = []`, заполняется в задаче 6 после реализации всех сущностей)
- [x] Создать `swax/config/errors.py` с пустым `__all__: list[str] = []` (заполняется в задаче 3)
- [x] Убедиться, что `python -c "import swax.config"` работает
- [x] Lint: `ruff check swax/config` — должен быть чистым

---

### Task 2: `swax/config/` — pydantic models `Config`, `GitConfig`, `SpecsConfig`

Реализовать три модели в трёх `location`-файлах согласно контракту. Это базовые дата-классы для persistence; методы — только pydantic-конструкторы.

**Usages relevant to this task:**
- `conventions`: pydantic kw_only, type hints обязательны.
- `pyyaml`: модели должны `model_dump(mode="json")` → YAML-safe dict (используется в задаче 5).

**Контрактные сущности (см. CODEMANIFEST):**
- `Config(git: GitConfig, specs: SpecsConfig)` — `Config.py`
- `GitConfig(url: str, location: str)` — `GitConfig.py`
- `SpecsConfig(type: Literal['swagger', 'openapi'], location: str)` — `SpecsConfig.py`

Примечание: эта задача НЕ модифицирует `errors.py` (он остаётся пустым до Task 3).

- [x] **Contract tests** (`tests/config/test_models_contract.py`): для каждой модели — `from swax.config import Config, GitConfig, SpecsConfig` успешен; конструктор требует keyword args (kw_only — `TypeError` на позиционный); `Config(git=..., specs=...)` round-trip через `model_dump()`. (Ожидаемый fail — `ImportError`.)
- [x] **Code**: создать `swax/config/Config.py`, `swax/config/GitConfig.py`, `swax/config/SpecsConfig.py` — каждый файл объявляет pydantic-модель с `model_config = ConfigDict(kw_only=True)`. `SpecsConfig.type: Literal["swagger", "openapi"]`.
- [x] **Interface verification**: `pytest tests/config/test_models_contract.py -v` — все должны пройти.
- [x] **Logic tests** (`tests/config/test_models_logic.py`): `Config` с валидными данными возвращается через `model_validate(dict)`; `SpecsConfig(type="invalid")` поднимает `ValidationError`; `GitConfig` принимает произвольные строки (no URL validation per contract).
- [x] **Debugging**: `pytest tests/config/ -v` — фиксить только код (не тесты), пока все тесты не пройдут.
- [x] **Contract re-verification**: kw_only enforced, type hints соответствуют сигнатурам контракта.
- [x] **Lint**: `ruff check swax/config/Config.py swax/config/GitConfig.py swax/config/SpecsConfig.py tests/config/test_models_*.py` — фиксить форматирование.

---

### Task 3: `swax/config/` — error entities

Реализовать 3 доменных исключения в одном `location` (`errors.py`). Все — pydantic-based или наследники `Exception` (решение исполнителя); критично — keyword-only с указанными полями.

**Usages relevant to this task:**
- `conventions`: доменные ошибки — стандартный паттерн.

**Контрактные сущности:**
- `MissingEnvironmentVariablesError(missing: list[str])` — `errors.py`
- `InvalidLLMProtocolError(value: str, allowed: tuple[str, ...])` — `errors.py`
- `InvalidLLMBaseURLError(value: str)` — `errors.py`

- [x] **Contract tests** (`tests/config/test_errors_contract.py`): `from swax.config import MissingEnvironmentVariablesError, InvalidLLMProtocolError, InvalidLLMBaseURLError` успешен; каждое исключение конструируется через kwargs и хранит поля как атрибуты (`exc.missing`, `exc.value`, `exc.allowed`).
- [x] **Code**: в `swax/config/errors.py` объявить 3 класса (наследники `Exception`), kw_only через `__init__` с keyword-only параметрами. Добавить их в `__all__` файла.
- [x] **Interface verification**: `pytest tests/config/test_errors_contract.py -v`
- [x] **Logic tests**: `MissingEnvironmentVariablesError(missing=["A"])` → `exc.missing == ["A"]`; `InvalidLLMProtocolError(value="ftp", allowed=("anthropic","openai"))` сохраняет кортеж; строковые repr включают значения полей (регрессия на будущий вывод в CLI).
- [x] **Debugging**: `pytest tests/config/ -v`
- [x] **Contract re-verification**: все 3 имени в `errors.py.__all__`; сигнатуры совпадают.
- [x] **Lint**: `ruff check swax/config/errors.py tests/config/test_errors_*.py`

---

### Task 4: `swax/config/` — env routines (`load_env`, `require_vars`, `parse_protocol`, `parse_base_url`)

Четыре routine-функции в одном `location` `env.py`. Алгоритмы зафиксированы в CODEMANIFEST.

**Usages relevant to this task:**
- `python-dotenv`: `load_dotenv(env_file, override=False)`.
- `conventions`: тесты — `monkeypatch.setenv`/`delenv`, не реальные `.env`-файлы (кроме `tmp_path`).

**Контрактные сущности:**
- `load_env(env_file: pathlib.Path)` — `env.py`
- `require_vars() -> vars: dict[str, str]` — `env.py`
- `parse_protocol(value: str) -> protocol: str` — `env.py`
- `parse_base_url(value: str) -> base_url: str` — `env.py`

**Алгоритмы (перенесены verbatim из design-doc §`swax/config/`):**

`load_env`:
1. `IF NOT env_file.exists(): return`
2. `load_dotenv(env_file, override=False)`

`require_vars` (REQUIRED_VARS = `("SWAX_LLM_PROTOCOL", "SWAX_LLM_BASE_URL", "SWAX_LLM_TOKEN")`):
1. FOR name IN REQUIRED_VARS: value = `os.environ.get(name)`; IF NOT value OR NOT value.strip(): missing.append(name)
2. IF missing: raise `MissingEnvironmentVariablesError(missing=missing)`
3. RETURN `{name: os.environ[name] FOR name IN REQUIRED_VARS}`

`parse_protocol`:
1. IF value NOT IN `("anthropic", "openai")`: raise `InvalidLLMProtocolError(value=value, allowed=("anthropic", "openai"))`
2. RETURN value

`parse_base_url`:
1. `stripped = value.rstrip("/")`
2. IF `stripped.endswith(("/v1", "/v2"))`: raise `InvalidLLMBaseURLError(value=value)`
3. RETURN stripped

- [x] **Contract tests** (`tests/config/test_env_contract.py`): `from swax.config import load_env, require_vars, parse_protocol, parse_base_url` успешен; сигнатуры (через `inspect`) соответствуют контракту.
- [x] **Code**: создать `swax/config/env.py` с 4 функциями. Определить `REQUIRED_VARS` и `ALLOWED_PROTOCOLS` как module-level константы. Импорты внутри клетки — relative (`from .errors import ...`).
- [x] **Interface verification**: `pytest tests/config/test_env_contract.py -v`
- [x] **Logic tests** (`tests/config/test_env_logic.py`):
  - `test_load_env_silent_on_missing_file` (см. design-doc, edge case) — `load_env(tmp_path / ".env")` не падает.
  - `test_load_env_does_not_override_shell_var` — `monkeypatch.setenv("SWAX_LLM_TOKEN", "shell")`, записать `.env` с другим значением, `load_env(path)` → shell var unchanged.
  - `test_require_vars_raises_on_missing_token` (см. design-doc, negative test) — `monkeypatch.delenv("SWAX_LLM_TOKEN")`, остальные установлены → raises.
  - `test_require_vars_whitespace_only_is_missing` — `setenv("SWAX_LLM_TOKEN", "   ")` → raises.
  - `test_require_vars_returns_mapping_when_all_present` — все 3 установлены → возвращаемый dict содержит все 3.
  - `test_parse_protocol_accepts_supported_values` (parametrize `["anthropic", "openai"]`, design-doc edge case).
  - `test_parse_protocol_rejects_unsupported` — `"ftp"` → `InvalidLLMProtocolError`.
  - `test_parse_base_url_rejects_versioned_segments` (parametrize `[".../v1", ".../v2/", ".../v1/"]`, design-doc edge case).
  - `test_parse_base_url_strips_trailing_slash` — `"https://x.com/"` → `"https://x.com"`.
- [x] **Debugging**: `pytest tests/config/ -v`
- [x] **Contract re-verification**: `SWAX_LLM_TOKEN` не появляется в логах; `require_vars` — lazy (не вызывается автоматически).
- [x] **Lint**: `ruff check swax/config/env.py tests/config/test_env_*.py`

---

### Task 5: `swax/config/` — storage routines (`load_config`, `save_config`)

Routine-функции в одном `location` `storage.py`. Round-trip с `Config`.

**Usages relevant to this task:**
- `pyyaml`: `yaml.safe_load`, `yaml.safe_dump(sort_keys=False, allow_unicode=True, default_flow_style=False)`, UTF-8.
- `conventions`: `tmp_path` для FS-тестов.

**Контрактные сущности:**
- `load_config(path: pathlib.Path) -> config: Config` — `storage.py`
- `save_config(config: Config, path: pathlib.Path)` — `storage.py`

**Алгоритмы (design-doc §`swax/config/`):**

`load_config`:
1. `raw_text = path.read_text(encoding="utf-8")`
2. `raw = yaml.safe_load(raw_text)`
3. RETURN `Config.model_validate(raw)`

`save_config`:
1. `payload = config.model_dump(mode="json")`
2. `path.parent.mkdir(parents=True, exist_ok=True)`
3. `yaml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)`
4. `path.write_text(yaml_text, encoding="utf-8")`

- [x] **Contract tests** (`tests/config/test_storage_contract.py`): `from swax.config import load_config, save_config` успешен; сигнатуры соответствуют.
- [x] **Code**: создать `swax/config/storage.py`. Импорт `Config` через relative.
- [x] **Interface verification**: `pytest tests/config/test_storage_contract.py -v`
- [x] **Logic tests** (`tests/config/test_storage_logic.py`):
  - `test_load_config_parses_valid_yaml` (design-doc positive test, verbatim assertions).
  - `test_save_config_creates_parents_and_writes_deterministic_yaml` (design-doc positive test, включая повторный `save_config` → идентичный файл).
  - `test_save_load_round_trip` — `save_config(c, p)` then `load_config(p)` → equal Config.
- [x] **Debugging**: `pytest tests/config/ -v`
- [x] **Contract re-verification**: `sort_keys=False`, `allow_unicode=True`, `default_flow_style=False`.
- [x] **Lint**: `ruff check swax/config/storage.py tests/config/test_storage_*.py`

---

### Task 6: `swax/config/` — facade `__init__.py` (infrastructure)

Закрыть фасад клетки: `__all__` содержит все 12 имён контракта.

- [x] В `swax/config/__init__.py` импортировать все 12 имён из соответствующих location-модулей и объявить `__all__` = `["Config", "GitConfig", "SpecsConfig", "MissingEnvironmentVariablesError", "InvalidLLMProtocolError", "InvalidLLMBaseURLError", "load_env", "require_vars", "parse_protocol", "parse_base_url", "load_config", "save_config"]`.
- [x] Verify facade accessibility: `python -c "from swax.config import Config, GitConfig, SpecsConfig, MissingEnvironmentVariablesError, InvalidLLMProtocolError, InvalidLLMBaseURLError, load_env, require_vars, parse_protocol, parse_base_url, load_config, save_config"`
- [x] Запустить все тесты клетки: `pytest tests/config/ -v` (55 passed)
- [x] Lint: `ruff check swax/config/__init__.py`

---

### Task 7: `swax/fs/` cell (skeleton + 2 routines + facade)

Клетка-лист с двумя routine-функциями в разных location. Выполняется как одна coding-задача (между сущностями нет связи по данным, но обе относятся к FS-layout).

**Usages relevant to this task:**
- `conventions`: `tmp_path` для всех FS-тестов, relative imports.

**Контрактные сущности:**
- `ensure_swax_dir(project_root: pathlib.Path) -> swax_dir: pathlib.Path` — `ensure_swax_dir.py`
- `copy_specs(source: pathlib.Path, destination: pathlib.Path)` — `copy_specs.py`

**Алгоритмы (design-doc §`swax/fs/`):**

`ensure_swax_dir`:
1. `swax_dir = project_root / ".swax"`
2. `swax_dir.mkdir(parents=True, exist_ok=True)`
3. RETURN swax_dir

`copy_specs` (ВАЖНО: `dirs_exist_ok=True`, default `symlinks=False`):
1. `destination.parent.mkdir(parents=True, exist_ok=True)`
2. `shutil.copytree(source, destination, dirs_exist_ok=True)`

- [x] **Contract tests** (`tests/fs/test_fs_contract.py`): `from swax.fs import ensure_swax_dir, copy_specs` успешен; сигнатуры соответствуют.
- [x] **Code**: создать `swax/fs/__init__.py` (пустой `__all__`), `swax/fs/ensure_swax_dir.py`, `swax/fs/copy_specs.py`.
- [x] **Interface verification**: `pytest tests/fs/test_fs_contract.py -v`
- [x] **Logic tests** (`tests/fs/test_fs_logic.py`):
  - `test_ensure_swax_dir_creates_directory_idempotent` — дважды вызвать, dir существует, возвращается путь `<root>/.swax`.
  - `test_copy_specs_merges_into_existing` — `tmp_path/src/a.yaml`, `tmp_path/dst/b.yaml` (pre-existing); после `copy_specs(src, dst)` — оба файла в dst.
  - `test_copy_specs_creates_destination_parent` — destination.parent не существует → создаётся.
  - `test_copy_specs_treats_symlinks_as_regular_files` — symlink в source копируется как regular file (проверить через `not (dst / "link").is_symlink()`).
- [x] **Debugging**: `pytest tests/fs/ -v`
- [x] **Contract re-verification**: `dirs_exist_ok=True`, symlinks копируются как regular files.
- [x] **Facade**: добавить `ensure_swax_dir, copy_specs` в `swax/fs/__init__.py.__all__`.
- [x] Verify facade: `python -c "from swax.fs import ensure_swax_dir, copy_specs"`
- [x] Lint: `ruff check swax/fs tests/fs`

---

### Task 8: `swax/git/` cell (skeleton + contextmanager + 2 errors + facade)

Клетка-лист: один contextmanager + 2 доменных исключения.

**Usages relevant to this task:**
- `gitpython`: `Repo.clone_from(url, tmp, depth=1)`, `GitCommandError` → `RepositoryCloneError`.
- `conventions`: `tmp_path`, `mocker.patch` в точке импорта.

**Контрактные сущности:**
- `clone_specs(repo_url: str, specs_location: str) -> Iterator[pathlib.Path]` — `clone_specs.py` (контекстный менеджер)
- `RepositoryCloneError(url: str, reason: str)` — `errors.py`
- `SpecsNotFoundError(path: pathlib.Path)` — `errors.py`

**Алгоритм (design-doc §`swax/git/`):**
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

- [x] **Contract tests** (`tests/git/test_git_contract.py`): `from swax.git import clone_specs, RepositoryCloneError, SpecsNotFoundError` успешен; `clone_specs` — callable, возвращает `Iterator`/contextmanager (`contextlib.contextmanager`); исключения kw_only.
- [x] **Code**: создать `swax/git/__init__.py`, `swax/git/clone_specs.py` (с `@contextlib.contextmanager`), `swax/git/errors.py`. Использовать `from git import Repo, GitCommandError` (absolute import SDK).
- [x] **Interface verification**: `pytest tests/git/test_git_contract.py -v`
- [x] **Logic tests** (`tests/git/test_git_logic.py`):
  - `test_clone_specs_yields_specs_path_on_success` — `mocker.patch("swax.git.clone_specs.Repo.clone_from")` no-op; создать `<tmp>/specs/api.yaml` вручную перед вызовом; `with clone_specs(url, "specs") as p: assert p.name == "specs"`.
  - `test_clone_specs_raises_repository_clone_error_on_git_error` — `Repo.clone_from.side_effect = GitCommandError("clone", "auth")` → `pytest.raises(RepositoryCloneError)`.
  - `test_clone_specs_raises_specs_not_found_when_subdir_missing` — successful clone, но `specs_location="missing/"` → `SpecsNotFoundError`.
  - `test_clone_specs_cleans_up_tempdir_on_clone_failure` (design-doc edge case) — spy на `tempfile.TemporaryDirectory` через `mocker.spy(tempfile, "TemporaryDirectory")`, затем `with pytest.raises(RepositoryCloneError): with clone_specs(url, "specs/"): pass`. Assert: `mock_tmp.return_value.__exit__.assert_called_once()` — корректно, поскольку spy оборачивает класс, и единственный вызов `TemporaryDirectory()` фиксируется. Дополнительно: проверить, что tempdir, на который ссылался `tmp_path` до raise, не существует на диске (через сохранённый path в side_effect).
- [x] **Debugging**: `pytest tests/git/ -v`
- [x] **Contract re-verification**: cleanup гарантирован, depth=1, без cred в URL.
- [x] **Facade**: добавить все 3 имени в `swax/git/__init__.py.__all__`.
- [x] Verify facade: `python -c "from swax.git import clone_specs, RepositoryCloneError, SpecsNotFoundError"`
- [x] Lint: `ruff check swax/git tests/git`

---

### Task 9: `swax/openapi/` cell (skeleton + 4 routines + error + facade)

Клетка-лист: 4 routine в разных location + 1 ошибка.

**Usages relevant to this task:**
- `prance`: `ResolvingParser(str(path), backend="openapi-spec-validator", strict=False, resolve_types=True)`, `parser.specification`.
- `pyyaml`: lightweight head-check в `discover_specs`.
- `conventions`: `tmp_path`, `mocker.patch` на `ResolvingParser` для негативных тестов.

**Контрактные сущности:**
- `parse_spec(spec_path) -> dict` — `parse_spec.py`
- `extract_paths(spec) -> list[str]` — `extract_paths.py`
- `extract_schemas(spec) -> dict` — `extract_schemas.py`
- `discover_specs(root) -> list[pathlib.Path]` — `discover_specs.py`
- `SpecParseError(path, reason)` — `errors.py`

**Алгоритмы (design-doc §`swax/openapi/`):**

`parse_spec`:
1. `try: parser = ResolvingParser(str(spec_path), backend="openapi-spec-validator", strict=False, resolve_types=True); RETURN parser.specification`
2. `except Exception as exc: raise SpecParseError(path=spec_path, reason=str(exc)) from exc`

`extract_paths`:
1. RETURN `sorted(spec.get("paths", {}).keys())`

`extract_schemas`:
1. IF `"components" IN spec`: RETURN `spec["components"].get("schemas", {})`
2. RETURN `spec.get("definitions", {})`

`discover_specs`:
1. result = []
2. FOR path IN `root.rglob("*")`:
   - IF `path.suffix.lower()` NOT IN `(".yaml", ".yml", ".json")`: continue
   - head_text = первая строка файла (или `"{}"` если пусто)
   - head = `yaml.safe_load(head_text)`
   - IF `isinstance(head, dict)` AND (`"openapi" IN head` OR `"swagger" IN head`): result.append(path)
3. RETURN `sorted(result)`

- [x] **Contract tests** (`tests/openapi/test_openapi_contract.py`): импорты 5 имён успешны; сигнатуры соответствуют.
- [x] **Code**: создать `swax/openapi/__init__.py`, 4 routine-модуля, `errors.py`.
- [x] **Interface verification**: `pytest tests/openapi/test_openapi_contract.py -v`
- [x] **Logic tests** (`tests/openapi/test_openapi_logic.py`):
  - `test_parse_spec_returns_dereferenced_dict` — `tmp_path/spec.yaml` с минимальной OpenAPI 3.x spec (с `$ref` внутри); `parse_spec` возвращает dict с резолвленным ref.
  - `test_parse_spec_raises_on_invalid_yaml` (design-doc negative test, verbatim) — `: not valid yaml:` → `SpecParseError`, `exc.path` совпадает, `exc.reason` — строка.
  - `test_extract_paths_returns_sorted_paths` — spec с `paths: {/b: ..., /a: ...}` → `["/a", "/b"]`.
  - `test_extract_paths_empty_when_no_paths` — spec без `paths` → `[]`.
  - `test_extract_schemas_returns_definitions_for_swagger_2` (design-doc edge case, verbatim) — spec с `definitions`, без `components` → возвращает `definitions`.
  - `test_extract_schemas_returns_components_schemas_for_openapi_3` — spec с `components.schemas` → возвращает её.
  - `test_discover_specs_filters_by_extension_and_head` — `tmp_path` с `api.yaml` (`openapi: 3.0.0` в head), `readme.md`, `data.json` (`{}` без ключа openapi/swagger) → возвращается только `api.yaml`.
  - `test_discover_specs_returns_sorted` — несколько файлов возвращаются в sorted-порядке.
- [x] **Debugging**: `pytest tests/openapi/ -v`
- [x] **Contract re-verification**: `$ref` резолвится (prance), paths sorted, swagger/openapi transparent.
- [x] **Facade**: 5 имён в `__all__`.
- [x] Verify facade: `python -c "from swax.openapi import parse_spec, extract_paths, extract_schemas, discover_specs, SpecParseError"`
- [x] Lint: `ruff check swax/openapi tests/openapi`

---

### Task 10: `swax/traceability/` cell (skeleton + Entity + 2 routines + facade)

Клетка-лист: Entity с методами и 2 routine для persistence.

**Usages relevant to this task:**
- `pyyaml`: deterministic dump.
- `conventions`: pydantic kw_only.

**Контрактные сущности:**
- `TraceabilityGraph(edges: dict[str, list[str]])` — `TraceabilityGraph.py`
  - property `edges -> dict[str, list[str]]`
  - method `add_edge(source: str, target: str)`
  - method `deduplicate()` — sorted set + removes self-loops + idempotent + удаляет пустые adjacency-lists (опционально, в design-doc помечено как cleanup)
- `load_traceability(path) -> TraceabilityGraph` — `storage.py`
- `save_traceability(graph, path)` — `storage.py`

**Алгоритмы (design-doc §`swax/traceability/`):**

`add_edge`:
```
self.edges.setdefault(source, []).append(target)
```

`deduplicate`:
```
FOR source IN list(self.edges.keys()):
  self.edges[source] = sorted(set(self.edges[source]))
  IF source IN self.edges[source]:
    self.edges[source] = [t for t in self.edges[source] if t != source]
  IF NOT self.edges[source]:
    del self.edges[source]  # optional cleanup
```

`load_traceability`:
1. `raw_text = path.read_text(encoding="utf-8") if path.exists() else ""`
2. `data = yaml.safe_load(raw_text) or {}`
3. `normalized = {k: list(v) for k, v in data.items()}`
4. RETURN `TraceabilityGraph(edges=normalized)`

`save_traceability`:
1. `payload = graph.model_dump(mode="json")`
2. `ordered = {k: sorted(v) for k, v in sorted(payload["edges"].items())}`
3. `path.parent.mkdir(parents=True, exist_ok=True)`
4. `yaml_text = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False)`
5. `path.write_text(yaml_text, encoding="utf-8")`

- [x] **Contract tests** (`tests/traceability/test_traceability_contract.py`): импорт 3 имён успешен; `TraceabilityGraph` имеет методы `add_edge`, `deduplicate` и property `edges`; kw_only.
- [x] **Code**: создать `swax/traceability/__init__.py`, `TraceabilityGraph.py` (pydantic model; `edges: dict[str, list[str]] = Field(default_factory=dict)`), `storage.py`.
- [x] **Interface verification**: `pytest tests/traceability/test_traceability_contract.py -v`
- [x] **Logic tests** (`tests/traceability/test_traceability_logic.py`):
  - `test_add_edge_appends_to_adjacency` — `g = TraceabilityGraph(edges={})`, `g.add_edge("/a", "/b")` дважды → `g.edges["/a"] == ["/b", "/b"]`.
  - `test_deduplicate_removes_duplicates_and_self_loops` — design-doc edge case `test_traceability_graph_deduplicate_idempotent_and_removes_self_loops` (verbatim).
  - `test_save_traceability_writes_sorted_yaml` — `g = TraceabilityGraph(edges={"/b": ["/a"], "/a": ["/b", "/a"]})`, `g.deduplicate()`, `save_traceability(g, p)` — content deterministic; повторный `save_traceability` → идентичный файл.
  - `test_load_traceability_handles_empty_file` — `path.write_text("")` → возвращается пустой graph.
  - `test_load_traceability_normalizes_values_to_list` — YAML с `/a: /b` (string вместо list) → `graph.edges["/a"] == ["/b"]`.
- [x] **Debugging**: `pytest tests/traceability/ -v`
- [x] **Contract re-verification**: idempotent deduplicate, deterministic dump.
- [x] **Facade**: 3 имени в `__all__`.
- [x] Verify facade: `python -c "from swax.traceability import TraceabilityGraph, load_traceability, save_traceability"`
- [x] Lint: `ruff check swax/traceability tests/traceability`

---

### Task 11: `swax/prompts/` cell (skeleton + 3 routines + facade)

Клетка-лист: 3 prompt-билдера, чистые функции.

**Usages relevant to this task:**
- `conventions`: deterministic output (sorted endpoints), no paths/secrets.

**Контрактные сущности:**
- `build_graph_system_prompt() -> str` — `build_graph_system_prompt.py` (без параметров, constant string)
- `build_graph_user_prompt(endpoints: list[str]) -> str` — `build_graph_user_prompt.py` (output contract: `{dependencies, uncertain}`)
- `build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> str` — `build_refine_user_prompt.py`

**Алгоритмы (design-doc §`swax/prompts/`):**

`build_graph_system_prompt`: вернуть константную строку, описывающую:
- Role: API dependency analyst
- Output contract: JSON object mapping source_path → [dependent_paths]
- Forbid prose around JSON
- Graph operates on paths only

`build_graph_user_prompt`:
```
payload = json.dumps({"endpoints": endpoints})
RETURN f"""Given these API endpoints:

{payload}

Return a JSON object with exactly two keys:
- "dependencies": object mapping source_path to list of dependent_paths
- "uncertain": list of uncertain dependency pairs as "/source -> /target" strings

The "uncertain" pairs will be refined in a follow-up turn with schema context."""
```

`build_refine_user_prompt`:
```
pairs_payload = json.dumps({"ambiguous_pairs": ambiguous_pairs})
schemas_payload = json.dumps({"schemas": schemas})
RETURN f"""Refine these ambiguous dependency pairs using schemas:

{pairs_payload}

{schemas_payload}

Return consolidated JSON object {source_path: [dependent_paths]}.
Do not introduce paths outside the provided endpoint universe."""
```

- [x] **Contract tests** (`tests/prompts/test_prompts_contract.py`): импорт 3 имён успешен; сигнатуры соответствуют.
- [x] **Code**: создать `swax/prompts/__init__.py` и 3 модуля. Использовать `json.dumps` (stdlib).
- [x] **Interface verification**: `pytest tests/prompts/test_prompts_contract.py -v`
- [x] **Logic tests** (`tests/prompts/test_prompts_logic.py`):
  - `test_system_prompt_mentions_role_and_constraints` — в строке есть "dependency", "JSON", "paths only", явное упоминание запрета prose вокруг JSON (например, "no prose" или "JSON only"), и явное упоминание, что graph operates on paths not HTTP methods.
  - `test_user_prompt_includes_endpoints_payload` — `build_graph_user_prompt(["/a", "/b"])` содержит `"/a"` и `"/b"`.
  - `test_user_prompt_states_two_keys_contract` — в строке упомянуты "dependencies" и "uncertain".
  - `test_refine_prompt_includes_pairs_and_schemas` — `build_refine_user_prompt(["/a -> /b"], {"User": {...}})` содержит `"/a -> /b"` и `"User"`.
  - `test_refine_prompt_forbids_external_paths` — в строке есть "Do not introduce paths".
  - `test_prompts_deterministic_for_same_input` — одинаковый input → идентичная строка.
- [x] **Debugging**: `pytest tests/prompts/ -v`
- [x] **Contract re-verification**: нет filesystem paths или credentials в выводе.
- [x] **Facade**: 3 имени в `__all__`.
- [x] Verify facade: `python -c "from swax.prompts import build_graph_system_prompt, build_graph_user_prompt, build_refine_user_prompt"`
- [x] Lint: `ruff check swax/prompts tests/prompts`

---

### Task 12: `swax/llm/` — cell skeleton + Protocol + errors (infrastructure + first coding)

Клетка уровня 1 (Imports из `swax/config`). Сначала каркас, протокол и 4 ошибки — без них адаптеры не компилируются.

**Usages relevant to this task:**
- `conventions`: Protocol structural typing, kw_only.
- `anthropic`/`openai`: cook-файлы описывают классы SDK, типизированные в сигнатурах адаптеров.

**Контрактные сущности:**
- `LLMClient` — Protocol, `LLMClient.py`
- `LLMCallError(reason)`, `LLMRateLimitedError(reason)`, `LLMResponseParseError(reason, excerpt)`, `UnsupportedLLMProtocolError(protocol)` — `errors.py`

- [x] **Contract tests** (`tests/llm/test_llm_contract.py`): `from swax.llm import LLMClient, LLMCallError, LLMRateLimitedError, LLMResponseParseError, UnsupportedLLMProtocolError` успешен; `LLMClient` — `typing.Protocol`; сигнатуры `ask`/`ask_multi_turn` извлекаются через `inspect.signature`.
- [x] **Code**: создать `swax/llm/__init__.py` (пустой), `swax/llm/LLMClient.py` с `class LLMClient(Protocol)`. Контракт `LLMClient()` — без параметров конструктора; методы объявляются как protocol-методы с `self` и телом `...` (ellipsis, без реализации):
  ```python
  from typing import Protocol

  class LLMClient(Protocol):
      def ask(self, system: str, user: str) -> str: ...
      def ask_multi_turn(self, system: str, messages: list[dict[str, str]]) -> str: ...
  ```
  Не использовать `@runtime_checkable` — контракт требует structural typing без runtime checks. `self` исключается из сигнатуры контракта (правило goga-cell-python). Создать `swax/llm/errors.py` с 4 исключениями.
- [x] **Interface verification**: `pytest tests/llm/test_llm_contract.py -v`
- [x] **Logic tests**: `LLMResponseParseError(reason="x", excerpt="y")` → поля сохранены; все ошибки наследуют `Exception`.
- [x] **Debugging**: `pytest tests/llm/ -v`
- [x] **Contract re-verification**: Protocol structural, без наследования.
- [x] **Lint**: `ruff check swax/llm/LLMClient.py swax/llm/errors.py tests/llm`

---

### Task 13: `swax/llm/` — `AnthropicAdapter` (Mutation)

Реализовать адаптер Anthropic поверх SDK.

**Usages relevant to this task:**
- `anthropic`: `Anthropic(api_key, base_url)`, `client.messages.create(model=DEFAULT_MODEL, max_tokens=4096, system=..., messages=...)`, `block.text for block in response.content if block.type == "text"`, mapping `RateLimitError → LLMRateLimitedError`, `APIError → LLMCallError`.

**Контрактные сущности:**
- `LLMClient::AnthropicAdapter(client)` — `AnthropicAdapter.py`
  - property `client -> Anthropic`
  - method `ask(system, user) -> str`
  - method `ask_multi_turn(system, messages) -> str`

**Алгоритм (design-doc §`swax/llm/`):**

`ask`:
```
try:
  response = client.messages.create(
    model=DEFAULT_MODEL, max_tokens=4096, system=system,
    messages=[{"role": "user", "content": user}],
  )
  RETURN "".join(b.text for b in response.content if b.type == "text")
except RateLimitError as exc:
  raise LLMRateLimitedError(reason=str(exc)) from exc
except APIError as exc:
  raise LLMCallError(reason=str(exc)) from exc
```

`ask_multi_turn`: идентично, но `messages=messages` вместо single-user list.

- [x] **Contract tests** (`tests/llm/test_anthropic_adapter_contract.py`): `from swax.llm import AnthropicAdapter` успешен; сигнатуры `ask`/`ask_multi_turn`/`__init__(client)` kw_only; `client` доступен как property.
- [x] **Code**: создать `swax/llm/AnthropicAdapter.py`. `DEFAULT_MODEL` — module-level константа (актуальный идентификатор модели Anthropic). Использовать `from anthropic import Anthropic, APIError, RateLimitError`.
- [x] **Interface verification**: `pytest tests/llm/test_anthropic_adapter_contract.py -v`
- [x] **Logic tests** (`tests/llm/test_anthropic_adapter_logic.py`) — все через `mocker.patch` на mock SDK client:
  - `test_ask_returns_concatenated_text_blocks` — mock client возвращает response с content=[text_block(type="text", text="hello "), text_block(type="text", text="world"), non_text_block(type="tool_use")] → `"hello world"`.
  - `test_ask_passes_system_and_user_to_sdk` — verify `messages.create` вызван с `system=...`, `messages=[{role:"user", content:user}]`, `model=DEFAULT_MODEL`, `max_tokens=4096`.
  - `test_ask_maps_rate_limit_error` — `messages.create.side_effect = RateLimitError(...)` → `pytest.raises(LLMRateLimitedError)`.
  - `test_ask_maps_api_error` — side_effect `APIError(...)` → `pytest.raises(LLMCallError)`.
  - `test_ask_multi_turn_preserves_messages_order` — verify `messages` kwarg передан как есть.
- [x] **Debugging**: `pytest tests/llm/ -v`
- [x] **Contract re-verification**: сигнатуры идентичны LLMClient protocol.
- [x] **Lint**: `ruff check swax/llm/AnthropicAdapter.py tests/llm/test_anthropic_adapter_*.py`

---

### Task 14: `swax/llm/` — `OpenAIAdapter` (Mutation)

Реализовать адаптер OpenAI.

**Usages relevant to this task:**
- `openai`: `OpenAI(api_key, base_url)`, `client.chat.completions.create(model=DEFAULT_MODEL, messages=...)`, `response.choices[0].message.content or ""`, mapping ошибок.

**Контрактные сущности:**
- `LLMClient::OpenAIAdapter(client)` — `OpenAIAdapter.py`
  - property `client -> OpenAI`
  - method `ask(system, user) -> str`
  - method `ask_multi_turn(system, messages) -> str`

**Алгоритм (design-doc §`swax/llm/`):**

`ask`:
```
try:
  response = client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=[
      {"role": "system", "content": system},
      {"role": "user", "content": user},
    ],
  )
  RETURN response.choices[0].message.content or ""
except RateLimitError as exc:
  raise LLMRateLimitedError(reason=str(exc)) from exc
except APIError as exc:
  raise LLMCallError(reason=str(exc)) from exc
```

`ask_multi_turn`:
```
prepended = [{"role": "system", "content": system}] + messages
# далее как ask, но messages=prepended
```

- [x] **Contract tests** (`tests/llm/test_openai_adapter_contract.py`): импорт, сигнатуры, property `client`.
- [x] **Code**: создать `swax/llm/OpenAIAdapter.py`. `DEFAULT_MODEL` — module-level (gpt-4o). `from openai import OpenAI, APIError, RateLimitError`.
- [x] **Interface verification**: `pytest tests/llm/test_openai_adapter_contract.py -v`
- [x] **Logic tests** (`tests/llm/test_openai_adapter_logic.py`):
  - `test_ask_returns_first_choice_content` — mock response с `choices[0].message.content = "hello"` → `"hello"`.
  - `test_ask_returns_empty_string_when_no_content` — `choices[0].message.content = None` → `""`.
  - `test_ask_prepends_system_message` — verify `messages=[{system}, {user}]`.
  - `test_ask_maps_rate_limit_and_api_errors` — parametrize двух side_effects.
  - `test_ask_multi_turn_prepends_system_to_history` — `messages=[{user}, {assistant}, {user}]` → SDK получает `[{system}, {user}, {assistant}, {user}]`.
- [x] **Debugging**: `pytest tests/llm/ -v`
- [x] **Contract re-verification**: сигнатуры идентичны protocol.
- [x] **Lint**: `ruff check swax/llm/OpenAIAdapter.py tests/llm/test_openai_adapter_*.py`

---

### Task 15: `swax/llm/` — factory routines (`build_anthropic_client`, `build_openai_client`, `build_llm_client`)

Routine-функции для конструирования SDK-клиентов и выбора адаптера по env.

**Usages relevant to this task:**
- `environment` (imported usage from `swax/config`): `require_vars` для fail-fast credential validation.
- `anthropic`/`openai`: SDK client constructors.

**Контрактные сущности:**
- `build_anthropic_client() -> Anthropic` — `build_anthropic_client.py`
- `build_openai_client() -> OpenAI` — `build_openai_client.py`
- `build_llm_client() -> LLMClient` — `build_llm_client.py`

**Алгоритмы (design-doc §`swax/llm/`):**

`build_anthropic_client`:
```
require_vars()
token = os.environ["SWAX_LLM_TOKEN"]
base_url = os.environ["SWAX_LLM_BASE_URL"]
RETURN Anthropic(api_key=token, base_url=base_url)
```

`build_openai_client`: идентично с `OpenAI(...)`.

`build_llm_client`:
```
protocol = os.environ.get("SWAX_LLM_PROTOCOL")
IF protocol == "anthropic": RETURN AnthropicAdapter(build_anthropic_client())
IF protocol == "openai": RETURN OpenAIAdapter(build_openai_client())
raise UnsupportedLLMProtocolError(protocol=protocol)
```

- [x] **Contract tests** (`tests/llm/test_build_client_contract.py`): импорт 3 имён успешен; сигнатуры соответствуют.
- [x] **Code**: создать 3 routine-модуля. Импорт `require_vars` через `from swax.config import require_vars` (абсолютный, поскольку это cross-cell). Импорт адаптеров relative.
- [x] **Interface verification**: `pytest tests/llm/test_build_client_contract.py -v`
- [x] **Logic tests** (`tests/llm/test_build_client_logic.py`):
  - `test_build_anthropic_client_reads_env` — `monkeypatch.setenv` 3 переменных, `mocker.patch("swax.llm.build_anthropic_client.Anthropic")` → verify вызван с `api_key=token, base_url=base_url`.
  - `test_build_anthropic_client_calls_require_vars_first` — без env → `MissingEnvironmentVariablesError`.
  - `test_build_openai_client_analogous` — аналогично.
  - `test_build_llm_client_returns_anthropic_adapter` — `SWAX_LLM_PROTOCOL=anthropic`, mock `build_anthropic_client` → возвращается `AnthropicAdapter` instance.
  - `test_build_llm_client_returns_openai_adapter` — аналогично для openai.
  - `test_build_llm_client_raises_on_unknown_protocol` — `SWAX_LLM_PROTOCOL=ftp` → `UnsupportedLLMProtocolError`.
- [x] **Debugging**: `pytest tests/llm/ -v`
- [x] **Contract re-verification**: `require_vars` вызывается первым (fail-fast); cred только из env.
- [x] **Facade**: добавить все 9 имён контракта в `swax/llm/__init__.py.__all__` (`LLMClient`, `AnthropicAdapter`, `OpenAIAdapter`, `LLMCallError`, `LLMRateLimitedError`, `LLMResponseParseError`, `UnsupportedLLMProtocolError`, `build_anthropic_client`, `build_openai_client`, `build_llm_client`).
- [x] Verify facade: `python -c "from swax.llm import LLMClient, AnthropicAdapter, OpenAIAdapter, LLMCallError, LLMRateLimitedError, LLMResponseParseError, UnsupportedLLMProtocolError, build_anthropic_client, build_openai_client, build_llm_client"`
- [x] Lint: `ruff check swax/llm tests/llm`

---

### Task 16: `swax/applications/init/` — `run_init` use-case

Use-case-оркестрация: Config → save → clone → copy.

**Usages relevant to this task:**
- `project-config`: `Config` assembly, `save_config` semantics.
- `specs-repository`: `clone_specs` context manager, propagated errors.
- `project-layout`: `ensure_swax_dir`, `copy_specs`.
- `conventions`: `mocker.patch` в точке импорта (на `swax.applications.init.clone_specs` и `.copy_specs`), `tmp_path`.

**Контрактные сущности:**
- `run_init(repo_url, specs_location, download_path, project_root)` — `run_init.py`

**Алгоритм (design-doc §`swax/applications/init/`):**
```
config = Config(
  git=GitConfig(url=repo_url, location=specs_location),
  specs=SpecsConfig(type="openapi", location=str(download_path)),
)
swax_dir = ensure_swax_dir(project_root)
save_config(config, swax_dir / "config.yml")
logger.info("init started", extra={"project_root": str(project_root)})
with clone_specs(repo_url, specs_location) as specs_path:
  copy_specs(source=specs_path, destination=download_path)
logger.info("init completed", extra={"project_root": str(project_root)})
```

- [x] **Contract tests** (`tests/applications/init/test_run_init_contract.py`): `from swax.applications.init import run_init` успешен; сигнатура через `inspect.signature` соответствует (`repo_url, specs_location, download_path, project_root`).
- [x] **Code**: создать `swax/applications/init/__init__.py` (пустой), `swax/applications/init/run_init.py`. Импорты: `from swax.config import Config, GitConfig, SpecsConfig, save_config`; `from swax.git import clone_specs`; `from swax.fs import ensure_swax_dir, copy_specs`. Логирование через `logging.getLogger(__name__)`.
- [x] **Interface verification**: `pytest tests/applications/init/test_run_init_contract.py -v`
- [x] **Logic tests** (`tests/applications/init/test_run_init_logic.py`):
  - `test_run_init_persists_config_then_copies_specs` (design-doc positive test, verbatim) — mocks `clone_specs`/`copy_specs`, asserts `config.yml` существует, `copy_specs` вызван ровно один раз, ordering через `mock_calls`.
  - `test_run_init_config_survives_clone_failure` (design-doc positive test Р7, verbatim) — `clone_specs.side_effect = RepositoryCloneError(...)`, asserts `config.yml` существует на диске, `copy_specs.assert_not_called()`.
  - `test_run_init_propagates_specs_not_found` — `clone_specs` поднимает `SpecsNotFoundError` → пробрасывается без catch.
- [x] **Debugging**: `pytest tests/applications/init/ -v`
- [x] **Contract re-verification**: config пишется ДО clone; cleanup гарантирован context manager-ом.
- [x] **Facade**: добавить `run_init` в `swax/applications/init/__init__.py.__all__`.
- [x] Verify facade: `python -c "from swax.applications.init import run_init"`
- [x] Lint: `ruff check swax/applications/init tests/applications/init`

---

### Task 17: `swax/applications/discover/` — `run_discover` use-case

Двухпроходный LLM-сценарий. Самая сложная задача — содержит 3 внутренних helper-а вне контракта.

**Usages relevant to this task:**
- `project-config`: `load_config`, `Config`.
- `environment`: `require_vars`.
- `parsing`: `discover_specs`, `parse_spec`.
- `extraction`: `extract_paths`, `extract_schemas`.
- `llm-transport`: `build_llm_client`, `LLMClient`, `LLMResponseParseError`.
- `traceability-llm-prompts`: prompt builders.
- `graph-lifecycle`: `TraceabilityGraph`, `save_traceability`.
- `json`: defensive parsing.
- `conventions`: `mocker.patch` на `build_llm_client`, `tmp_path`.

**Контрактные сущности:**
- `run_discover(project_root: pathlib.Path)` — `run_discover.py`

**Внутренние helper-ы (в `run_discover.py`, вне контракта):**

`_strip_prose_and_fences(raw: str) -> str`:
```
first_brace = raw.find("{")
last_brace = raw.rfind("}")
IF first_brace == -1 OR last_brace == -1 OR first_brace > last_brace:
  return raw
return raw[first_brace : last_brace + 1]
```

`_validate_dependency_shape(d: dict) -> None`:
```
for k, v in d.items():
  if not isinstance(k, str) or not isinstance(v, list) or not all(isinstance(x, str) for x in v):
    raise LLMResponseParseError(reason="shape mismatch: expected dict[str, list[str]]", excerpt="...")
```

`_parse_llm_json(raw: str, *, first_pass: bool) -> tuple[dict[str, list[str]], list[str]]`:
```
stripped = _strip_prose_and_fences(raw)
try:
  parsed = json.loads(stripped)
except json.JSONDecodeError as exc:
  raise LLMResponseParseError(reason=str(exc), excerpt=stripped[:200]) from exc
if not isinstance(parsed, dict):
  raise LLMResponseParseError(reason="not a dict", excerpt=stripped[:200])
IF first_pass:
  IF set(parsed.keys()) != {"dependencies", "uncertain"}:
    raise LLMResponseParseError(reason="first pass: keys must be dependencies+uncertain", excerpt=stripped[:200])
  deps = parsed["dependencies"]; unc = parsed["uncertain"]
  _validate_dependency_shape(deps)
  IF not isinstance(unc, list) or not all(isinstance(x, str) for x in unc):
    raise LLMResponseParseError(reason="uncertain: must be list[str]", excerpt=stripped[:200])
  return deps, unc
ELSE:
  _validate_dependency_shape(parsed)
  return parsed, []
```

**Алгоритм `run_discover` (design-doc §`swax/applications/discover/`):**
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
16. ambiguous_pairs = uncertain
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

**Errors propagated (без catch):** `MissingEnvironmentVariablesError`, `SpecParseError`, `LLMCallError`, `LLMRateLimitedError`, `UnsupportedLLMProtocolError`, `LLMResponseParseError`.

- [x] **Contract tests** (`tests/applications/discover/test_run_discover_contract.py`): `from swax.applications.discover import run_discover` успешен; сигнатура `run_discover(project_root: pathlib.Path)`.
- [x] **Code**: создать `swax/applications/discover/__init__.py` (пустой), `swax/applications/discover/run_discover.py` с `run_discover` + 3 private helper-ами. Cross-cell импорты абсолютные (`from swax.config import ...`, и т.д.). `json` — stdlib-импорт (inline Usages из CODEMANIFEST, не cross-cell).
- [x] **Interface verification**: `pytest tests/applications/discover/test_run_discover_contract.py -v`
- [x] **Logic tests** (`tests/applications/discover/test_run_discover_logic.py`) — критически важно покрыть все сценарии из design-doc:
  - `test_run_discover_builds_graph_with_two_llm_passes` (design-doc positive test, verbatim assertions — включая messages structure `[user, assistant, user]`).
  - `test_run_discover_raises_llm_response_parse_error_on_invalid_first_pass` (design-doc Р6a, verbatim — `"Sorry, here is my answer: {...}"` без ключа `uncertain`, asserts `ask_multi_turn.assert_not_called()`).
  - `test_run_discover_passes_uncertain_pairs_to_refine` (design-doc Р6b, verbatim — uncertain `["/users -> /orders"]` попадает в refine message).
  - `test_run_discover_overwrites_existing_traceability_yml` (design-doc edge case, verbatim).
  - `test_run_discover_propagates_domain_errors` — parametrize 5 доменных исключений (`MissingEnvironmentVariablesError`, `SpecParseError`, `LLMCallError`, `LLMRateLimitedError`, `UnsupportedLLMProtocolError`); `LLMResponseParseError` покрывается отдельным тестом Р6a `test_run_discover_raises_llm_response_parse_error_on_invalid_first_pass`. Для каждого параметра: замокать соответствующий слой так, чтобы исключение пробрасывалось, asserts `pytest.raises`.
  - `test_parse_llm_json_helper_strips_prose_around_json` — unit-test на `_parse_llm_json`: `'text {"a": ["b"]} more'` → `({"a": ["b"]}, [])` при `first_pass=False`.
  - `test_parse_llm_json_helper_rejects_non_dict` — `'[1, 2]'` → `LLMResponseParseError(reason="not a dict")`.
  - `test_parse_llm_json_helper_validates_shape` — `{"a": "not_a_list"}` → `LLMResponseParseError(reason="shape mismatch")`.
- [x] **Debugging**: `pytest tests/applications/discover/ -v`
- [x] **Contract re-verification**: paths only в графе; defensive parsing активен; `SWAX_LLM_TOKEN` не в логах.
- [x] **Facade**: добавить `run_discover` в `__all__`.
- [x] Verify facade: `python -c "from swax.applications.discover import run_discover"`
- [x] Lint: `ruff check swax/applications/discover tests/applications/discover`

---

### Task 18: `swax/applications/` facade (infrastructure)

Фасад-агрегатор с re-export-ами `run_init_handler`, `run_discover_handler`.

- [x] Создать `swax/applications/__init__.py` с `from swax.applications.init import run_init as run_init_handler`, `from swax.applications.discover import run_discover as run_discover_handler`, `__all__ = ["run_init_handler", "run_discover_handler"]`.
- [x] Verify facade: `python -c "from swax.applications import run_init_handler, run_discover_handler; assert callable(run_init_handler) and callable(run_discover_handler)"`
- [x] Lint: `ruff check swax/applications/__init__.py`

---

### Task 19: `swax/commands/init/` — Click handler `init`

Тонкий CLI-обработчик: промпты + exception mapping.

**Usages relevant to this task:**
- `click`: `@click.command`, `click.prompt`, `click.ClickException`, `@click.pass_obj`, `click.testing.CliRunner`.
- `cli-facade`: `SwaxContext` access pattern.
- `init-usage`: `run_init` semantics.
- `specs-repository`: `RepositoryCloneError`, `SpecsNotFoundError`.
- `conventions`: `mocker.patch` на `swax.commands.init.run_init`, `CliRunner.invoke`.

**Контрактные сущности:**
- `init(ctx: click.Context)` — `init.py`

**Алгоритм (design-doc §`swax/commands/init/`):**
```
@click.command()
@click.pass_obj
def init(ctx):  # ctx is SwaxContext
  repo_url = click.prompt("Repository URL")
  specs_location = click.prompt("Path to specs inside the repo")
  download_path = pathlib.Path(click.prompt("Local download path"))
  project_root = pathlib.Path.cwd()
  try:
    run_init(repo_url, specs_location, download_path, project_root)
  except RepositoryCloneError as exc:
    raise click.ClickException(f"Failed to clone {exc.url}: {exc.reason}") from exc
  except SpecsNotFoundError as exc:
    raise click.ClickException(f"Specs not found at {exc.path}") from exc
```

- [x] **Contract tests** (`tests/commands/init/test_init_contract.py`): `from swax.commands.init import init` успешен; `init` — Click command (`isinstance(init, click.Command)` или `init.callback` существует).
- [x] **Code**: создать `swax/commands/init/__init__.py` (пустой), `swax/commands/init/init.py`. Импорты: `from swax.applications import run_init_handler as run_init` (facade `swax.applications` экспортирует alias `run_init_handler` через embedding); `from swax.git import RepositoryCloneError, SpecsNotFoundError`; `from swax.cli import SwaxContext` (для type hint, не используется в логике).
- [x] **Interface verification**: `pytest tests/commands/init/test_init_contract.py -v`
- [x] **Logic tests** (`tests/commands/init/test_init_logic.py`):
  - `test_init_invokes_run_init_with_prompted_values` — `CliRunner`, mock `run_init`, `input="u\nl\n./p\n"`, asserts mock вызван с `("u", "l", Path("./p"), Path.cwd())`.
  - `test_init_handler_maps_repository_clone_error` (design-doc negative test, verbatim) — exit_code == 1, output содержит `"Failed to clone"` и `"auth failed"`.
  - `test_init_handler_maps_specs_not_found_error` — `run_init.side_effect = SpecsNotFoundError(Path("/x"))` → exit_code 1, output содержит `"Specs not found at"`.
- [x] **Debugging**: `pytest tests/commands/init/ -v`
- [x] **Contract re-verification**: только 2 documented exceptions мапятся, generic Exception не ловится.
- [x] **Facade**: добавить `init` в `__all__`.
- [x] Verify facade: `python -c "from swax.commands.init import init"`
- [x] Lint: `ruff check swax/commands/init tests/commands/init`

---

### Task 20: `swax/commands/discover/` — Click handler `discover`

Тонкий CLI-обработчик: exception mapping для 6 доменных ошибок.

**Usages relevant to this task:**
- `click`: `@click.command`, `@click.pass_obj`, `click.ClickException`, `CliRunner`.
- `cli-facade`: `SwaxContext`.
- `discover-usage`: `run_discover` semantics.
- `environment`, `parsing`, `llm-transport`: доменные исключения.

**Контрактные сущности:**
- `discover(ctx: click.Context)` — `discover.py`

**Алгоритм (design-doc §`swax/commands/discover/`):**
```
@click.command()
@click.pass_obj
def discover(ctx):  # SwaxContext, intentionally unused
  project_root = pathlib.Path.cwd()
  try:
    run_discover(project_root)
  except MissingEnvironmentVariablesError as exc:
    raise click.ClickException(f"Missing env vars: {', '.join(exc.missing)}") from exc
  except SpecParseError as exc:
    raise click.ClickException(f"Failed to parse {exc.path}: {exc.reason}") from exc
  except LLMRateLimitedError:
    raise click.ClickException("LLM rate limited; retry later")
  except LLMCallError as exc:
    raise click.ClickException(f"LLM call failed: {exc.reason}") from exc
  except UnsupportedLLMProtocolError as exc:
    raise click.ClickException(f"Unsupported LLM protocol: {exc.protocol}") from exc
  except LLMResponseParseError as exc:
    raise click.ClickException(f"LLM response parse failed: {exc.reason}") from exc
```

- [x] **Contract tests** (`tests/commands/discover/test_discover_contract.py`): импорт `discover` успешен; `isinstance(discover, click.Command)`.
- [x] **Code**: создать `swax/commands/discover/__init__.py` (пустой), `swax/commands/discover/discover.py`. Импорты: `from swax.applications import run_discover_handler as run_discover` (facade alias через embedding); доменные исключения из `swax.config`, `swax.openapi`, `swax.llm` напрямую (не через facade). Cross-cell импорты абсолютные.
- [x] **Interface verification**: `pytest tests/commands/discover/test_discover_contract.py -v`
- [x] **Logic tests** (`tests/commands/discover/test_discover_logic.py`):
  - `test_discover_handler_maps_domain_errors` (design-doc Р8, parametrized × 6, verbatim) — все 6 исключений маппятся в `click.ClickException` с ожидаемой подстрокой.
  - `test_discover_handler_no_prompts` — invoke без stdin input, mock `run_discover` успехом → exit_code 0.
- [x] **Debugging**: `pytest tests/commands/discover/ -v`
- [x] **Contract re-verification**: 6 documented exceptions; `SWAX_LLM_TOKEN` не в сообщениях.
- [x] **Facade**: добавить `discover` в `__all__`.
- [x] Verify facade: `python -c "from swax.commands.discover import discover"`
- [x] Lint: `ruff check swax/commands/discover tests/commands/discover`

---

### Task 21: `swax/commands/` facade (infrastructure)

Фасад-агрегатор с re-export-ами `init_handler`, `discover_handler`.

- [x] Создать `swax/commands/__init__.py` с `from swax.commands.init import init as init_handler`, `from swax.commands.discover import discover as discover_handler`, `__all__ = ["init_handler", "discover_handler"]`.
- [x] Verify facade: `python -c "from swax.commands import init_handler, discover_handler; assert isinstance(init_handler, click.Command) and isinstance(discover_handler, click.Command)"`
- [x] Lint: `ruff check swax/commands/__init__.py`

---

### Task 22: `swax/cli/` — `main` group + `SwaxContext` + `__main__`

Точка входа CLI.

**Usages relevant to this task:**
- `click`: `@click.group`, `click.Path(exists=False, dir_okay=False, path_type=pathlib.Path)`, `@click.pass_context`, `show_default=True`, `default=".env"`.
- `environment`: `load_env`.
- `project-config`: `Config` shape для `SwaxContext.config: Config | None`.
- `conventions`: pydantic kw_only, `CliRunner`.

**Контрактные сущности:**
- `main(ctx: click.Context, env_file: pathlib.Path)` — `main.py`
- `SwaxContext(env_file: pathlib.Path)` — `SwaxContext.py`
  - property `env_file -> pathlib.Path`
  - property `config -> Config | None` (default `None`)

**Вне контракта (обязательно):**
- `swax/cli/__main__.py` — lazy registration:
  ```
  from swax.cli.main import main
  from swax.commands import init_handler, discover_handler
  main.add_command(init_handler, name="init")
  main.add_command(discover_handler, name="discover")
  if __name__ == "__main__":
      main()
  ```

**Алгоритм `main` (design-doc §`swax/cli/`):**
```
@click.group()
@click.option("--env-file", type=click.Path(exists=False, dir_okay=False, path_type=pathlib.Path),
              default=".env", show_default=True)
@click.pass_context
def main(ctx, env_file):
  load_env(env_file)
  ctx.obj = SwaxContext(env_file=env_file)
```

- [x] **Contract tests** (`tests/cli/test_main_contract.py`): `from swax.cli import main, SwaxContext` успешен; `isinstance(main, click.Group)`; `SwaxContext(env_file=Path(".env"))` — kw_only, property `env_file` и `config` доступны; `config` по умолчанию `None`.
- [x] **Code**: создать `swax/cli/__init__.py` (`__all__ = ["main", "SwaxContext"]`), `swax/cli/main.py`, `swax/cli/SwaxContext.py`, `swax/cli/__main__.py`. Cross-cell импорт `from swax.config import load_env, load_config, Config` (контрактный). Логирование `load_env` не нужно.
- [x] **Interface verification**: `pytest tests/cli/test_main_contract.py -v`
- [x] **Logic tests** (`tests/cli/test_main_logic.py`):
  - `test_main_loads_env_file_when_exists` — `tmp_path/.env` с `SWAX_LLM_TOKEN=fromfile`, `monkeypatch.delenv` (если есть), `CliRunner().invoke(main, ["--env-file", str(tmp_path/".env"), "--help"])` — invoke только для группы; проверить `os.environ["SWAX_LLM_TOKEN"] == "fromfile"` после invocation (group callback исполняется).
  - `test_main_silent_on_missing_env_file` — несуществующий `--env-file` → exit_code 0 (с `--help` или без подкоманды).
  - `test_main_sets_swax_context_with_env_file` — invoke через CliRunner с подкомандой (mock-ой), проверка `ctx.obj.env_file` через custom command.
  - `test_main_registers_init_and_discover_lazily` — invoke `python -m swax.cli --help` или `CliRunner` + импорт `__main__`, verify `init` и `discover` присутствуют в `main.commands`.
  - `test_swax_context_default_config_is_none` — `SwaxContext(env_file=Path(".env")).config is None`.
  - `test_entry_point_registered` — `pyproject.toml` `[project.scripts]` содержит `swax = "swax.cli.__main__:main"` (парсить через `tomllib`).
- [x] **Debugging**: `pytest tests/cli/ -v`
- [x] **Contract re-verification**: `exists=False`, lazy registration в `__main__.py`, не в `__init__.py`.
- [x] Verify facade: `python -c "from swax.cli import main, SwaxContext"`
- [x] Lint: `ruff check swax/cli tests/cli`

---

### Task 23: Integration tests — end-to-end `swax init` + `swax discover`

Сквозные сценарии через `CliRunner` с замокированными SDK/git/LLM.

**Usages relevant to this task:**
- `click`: `CliRunner`.
- `gitpython`: можно использовать локальный git-репозиторий в `tmp_path` (без mock) для реалистичности `init`.
- Все cell-level usages, упомянутые в design-doc.

- [ ] Создать `tests/integration/test_init_and_discover.py`.
- [ ] `test_swax_init_end_to_end_with_local_repo` — создать локальный bare git-репозиторий в `tmp_path/remote` с `specs/api.yaml`, `CliRunner().invoke(main, ["--env-file", ".env", "init"], input="...")`, asserts: `.swax/config.yml` существует, `download_path/api.yaml` существует, exit_code 0.
- [ ] `test_swax_discover_end_to_end_with_mocked_llm` — `tmp_path` с `.swax/config.yml`, `specs/api.yaml`; `mocker.patch("swax.applications.discover.build_llm_client")` returns mock; mock `ask`/`ask_multi_turn` возвращают валидные JSON; `monkeypatch.setenv` SWAX_LLM_*; `CliRunner().invoke(main, [...])` → asserts exit_code 0, `.swax/traceability.yml` существует с ожидаемым графом.
- [ ] `test_swax_full_pipeline_init_then_discover` — объединить предыдущие два: после `init` (с local repo + mock build_llm_client) сразу `discover`, asserts файлы графа корректны.
- [ ] Run validation: `pytest tests/integration/ -v`

---

## Validation Commands

- `pytest tests/ -v`: запустить все тесты проекта.
- `pytest tests/<cell>/ -v`: запустить тесты одной клетки.
- `ruff check swax tests`: линтер (включая `I`, `N`, `PL`, `PTH`, `C90` — см. `pyproject.toml`).
- `ruff format --check swax tests`: проверка форматирования.
- `python -c "from swax.<cell> import <entity>"`: smoke-check фасада клетки (команды указаны в задачах 6–22).
- `python -c "from swax.cli import main; main(['--help'])"`: проверить, что entry point кликабелен и показывает подкоманды `init`/`discover`.
- `python -m swax.cli --help`: альтернативная проверка entry point через `__main__`.
- `mypy swax` (опционально, если установлен): статическая типизация.

---

## Completion Criteria

- [ ] Каждое контрактное entity реализовано в правильном `location`.
- [ ] Каждое контрактное entity доступно из фасада своей клетки (`__init__.py.__all__`).
- [ ] Свойства и методы соответствуют объявленным сигнатурам.
- [ ] Аннотации/Algorithm-ы отражены в поведении (verified логическими тестами).
- [ ] Контрактные зависимости (Imports.Types/Usages) разрешены: cross-cell импорты работают.
- [ ] Re-exports `run_init_handler`, `run_discover_handler`, `init_handler`, `discover_handler` доступны из соответствующих фасадов.
- [ ] Каждая coding-задача прошла TDD-цикл (контракт-тесты → код → interface verification → logic-тесты → debugging → re-verification → lint).
- [ ] Контракт-тесты и logic-тесты покрывают фасад, API и поведение в каждой coding-задаче.
- [ ] Интеграционные тесты покрывают end-to-end сценарии `swax init` и `swax discover`.
- [ ] Ни одна граница клетки не была расширена — новые клетки не создавались.
- [ ] `CODEMANIFEST` файлы и `.usages/` не модифицировались (read-only).
- [ ] Все команды валидации проходят.
- [ ] Каждое Usages-указание упомянуто минимум в одной задаче (см. таблицу выше).
