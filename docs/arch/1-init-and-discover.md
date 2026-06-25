# Architecture Plan: Swax — init + discover

## Topic

**`1-init-and-discover`** — фундамент CLI Swax: каркас CLI + 2 команды (init, discover) + 6 инфраструктурных/доменных пакетов + application-слой.

План сохранён в `docs/arch/1-init-and-discover.md`.

**Все ячейки создаются заново** (greenfield-задача). Существующей архитектуры нет (`goga schema` возвращает `[]`). Каталог `swax/` пуст.

---

## Implementation Order

Ячейки упорядочены снизу вверх (листья → корень). Каждая ячейка реализуется только после того, как все её зависимости (через `Imports`) уже реализованы.

| # | Ячейка | Обоснование порядка |
|---|------|-------------------|
| 1 | `swax/config/` | Листовая ячейка — нет Imports.Types. Предоставляет Config, GitConfig, SpecsConfig, env-валидаторы, доменные исключения. |
| 2 | `swax/fs/` | Листовая ячейка — нет Imports.Types. Предоставляет ensure_swax_dir, copy_specs. |
| 3 | `swax/git/` | Листовая ячейка — нет Imports.Types. Предоставляет clone_specs, RepositoryCloneError, SpecsNotFoundError. |
| 4 | `swax/openapi/` | Листовая ячейка — нет Imports.Types. Предоставляет parse_spec, extract_paths, extract_schemas, discover_specs, SpecParseError. |
| 5 | `swax/traceability/` | Листовая ячейка — нет Imports.Types. Предоставляет TraceabilityGraph, load_traceability, save_traceability. |
| 6 | `swax/prompts/` | Листовая ячейка — нет Imports.Types. Предоставляет промпт-билдеры для LLM. |
| 7 | `swax/llm/` | Зависит от `swax/config/` (require_vars, MissingEnvironmentVariablesError). Предоставляет LLMClient protocol, адаптеры, фабрику. |
| 8 | `swax/applications/init/` | Зависит от `config/`, `git/`, `fs/`. Предоставляет use-case run_init. |
| 9 | `swax/applications/discover/` | Зависит от `config/`, `openapi/`, `llm/`, `prompts/`, `traceability/`. Предоставляет use-case run_discover. |
| 10 | `swax/commands/init/` | Зависит от `cli/` (SwaxContext), `applications/init/`, `git/` (ошибки). Предоставляет Click-handler init. |
| 11 | `swax/commands/discover/` | Зависит от `cli/`, `applications/discover/`, `config/`, `openapi/`, `llm/` (ошибки). Предоставляет Click-handler discover. |
| 12 | `swax/cli/` | Зависит от `config/` (load_env). Точка входа CLI + SwaxContext. Команды регистрируются лениво в `__main__.py`. |

**Ключевое замечание по порядку 10-12:** ячейки `commands/*` и `cli/` имеют двунаправленную связь (commands импортируют SwaxContext из cli, а cli регистрирует команды в `__main__.py`). Это НЕ цикл в CODEMANIFEST Imports: `cli/CODEMANIFEST` импортирует только `load_env` из `config/`, без imports из `commands/`. Регистрация команд — код времени выполнения в `__main__.py`, что не отражается в контракте. Поэтому `cli/` можно реализовать последней (после команд) или параллельно с ними.

---

## Artifacts

Все 12 ячеек создаются заново. Для каждой: CODEMANIFEST (полное DSL-содержимое) + `.usages/` файлы.

---

### Cell 1/12: `swax/config/` (created anew)

#### CODEMANIFEST: `swax/config/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md
  pyyaml: .goga/usages/cooks/pyyaml.md
  python-dotenv: .goga/usages/cooks/python-dotenv.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `pyyaml` for serialization of `Config` to `.swax/config.yml`.
  Use `python-dotenv` for `.env` loading and `SWAX_*` validation.
  
  All pydantic models use `kw_only=True`.
  Use `Optional[...]` only for fields meaning explicit absence.
  Use relative imports inside the cell.
  Log without secrets — `SWAX_LLM_TOKEN` must never appear in logs.

---

"Config(git: GitConfig, specs: SpecsConfig)":
  location: Config.py
  annotations: |
    Root configuration of a Swax project, stored at `.swax/config.yml`.
    
    `git`: git repository coordinates — clone URL and path to specs inside the repo.
    `specs`: local layout of downloaded specifications — declared type and download path.
    
    Use `pyyaml` for serialization via `save_config` / `load_config`.
    Use `conventions` for pydantic model rules.
    
    Constraints:
    - Fields are required (no defaults) — a project without git or specs is invalid.

"GitConfig(url: str, location: str)":
  location: GitConfig.py
  annotations: |
    Coordinates of the remote git repository holding the API specifications.
    
    `url`: clone URL consumed by `clone_specs`.
    `location`: subdirectory inside the repo where specs live.
    
    Constraints:
    - `url` must be a valid clone target for GitPython (no embedded tokens).

"SpecsConfig(type: Literal['swagger', 'openapi'], location: str)":
  location: SpecsConfig.py
  annotations: |
    Local layout of downloaded specifications.
    
    `type`: declared spec format — constrained to `'swagger'` or `'openapi'` via `Literal`; pydantic rejects any other value at validation time.
    `location`: local download path where `copy_specs` writes specs.
    
    Constraints:
    - `type` declares the format but does not drive parsing — Prance auto-detects the actual version at parse time.

"MissingEnvironmentVariablesError(missing: list[str])":
  location: errors.py
  annotations: |
    Raised by `require_vars` when one or more mandatory `SWAX_*` environment variables are unset.
    
    `missing`: list of missing variable names, surfaced to the user.

"InvalidLLMProtocolError(value: str, allowed: tuple[str, ...])":
  location: errors.py
  annotations: |
    Raised by `parse_protocol` when `SWAX_LLM_PROTOCOL` is neither `"anthropic"` nor `"openai"`.
    
    `value`: the offending value submitted by the user.
    `allowed`: the accepted protocol identifiers.

"InvalidLLMBaseURLError(value: str)":
  location: errors.py
  annotations: |
    Raised by `parse_base_url` when `SWAX_LLM_BASE_URL` ends with a version segment (`/v1`, `/v2`).
    
    `value`: the offending URL.

"load_env(env_file: pathlib.Path) -> None":
  location: env.py
  annotations: |
    Load `.env` into the process environment before any command handler runs.
    
    `env_file`: path to the dotenv file passed via `--env-file`.
    
    Algorithm:
    1. If `env_file` does not exist, return without error.
    2. Call `load_dotenv(env_file, override=False)` so real shell variables win.
    
    Requirements:
    - Must be called from the CLI group callback, before subcommands execute.
    
    Use `python-dotenv` for the loading semantics.

"require_vars() -> vars: dict[str, str]":
  location: env.py
  annotations: |
    Validate that all mandatory `SWAX_*` variables are present in the environment.
    
    `vars`: mapping of variable name to its value, returned for caller convenience.
    
    Algorithm:
    1. Read each name in `REQUIRED_VARS` from `os.environ`.
    2. Collect names whose value is missing or contains only whitespace (strip before checking).
    3. If any are missing, raise `MissingEnvironmentVariablesError`.
    4. Otherwise return the mapping.
    
    Requirements:
    - Run lazily — only called from `run_discover` (and later `run_update`); `run_init` does not need LLM credentials.
    
    Constraints:
    - Whitespace-only values are treated as missing — reject rather than silently accept.
    
    Use `python-dotenv` for the REQUIRED_VARS list.

"parse_protocol(value: str) -> protocol: str":
  location: env.py
  annotations: |
    Validate that `SWAX_LLM_PROTOCOL` is a supported provider identifier.
    
    `value`: raw env value.
    `protocol`: the validated protocol string, unchanged.
    
    Algorithm:
    1. If `value` not in `("anthropic", "openai")`, raise `InvalidLLMProtocolError`.
    2. Return `value`.
    
    Use `python-dotenv` for the ALLOWED_PROTOCOLS list.

"parse_base_url(value: str) -> base_url: str":
  location: env.py
  annotations: |
    Reject `SWAX_LLM_BASE_URL` values that include a version segment.
    
    `value`: raw env value.
    `base_url`: the validated URL, unchanged.
    
    Algorithm:
    1. Strip trailing slashes.
    2. If the result ends with `/v1` or `/v2`, raise `InvalidLLMBaseURLError`.
    3. Return the stripped URL.
    
    Use `python-dotenv` for the version-segment check.

"load_config(path: pathlib.Path) -> config: Config":
  location: storage.py
  annotations: |
    Read `.swax/config.yml` and validate it into a `Config` model.
    
    `path`: path to the config file.
    `config`: the parsed and validated configuration.
    
    Algorithm:
    1. Read file text as UTF-8.
    2. `yaml.safe_load` the contents.
    3. `Config.model_validate(raw)` to enforce schema.
    
    Requirements:
    - Use `yaml.safe_load` only — never `yaml.load`.
    
    Use `pyyaml` for the loading pattern.

"save_config(config: Config, path: pathlib.Path) -> None":
  location: storage.py
  annotations: |
    Persist `Config` to `.swax/config.yml` deterministically.
    
    `config`: the configuration to write.
    `path`: destination file path.
    
    Algorithm:
    1. `config.model_dump(mode="json")` to get YAML-safe primitives.
    2. Create parent directories.
    3. `yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)`.
    4. Write text as UTF-8.
    
    Requirements:
    - Output must be stable across runs for clean diffs.
    
    Use `pyyaml` for the dumping pattern.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Project configuration, environment variables, and `SWAX_*` validation.
```

#### .usages file: `swax/config/.usages/project-config.md`

```md
# Project configuration — `.swax/config.yml`

## Предметная область

Шаблоны чтения и записи конфигурации проекта Swax. Целевая аудитория: cell-ы `applications/init/` (записывает конфиг после интерактивного опроса) и `applications/discover/` (читает конфиг для путей к спецификациям).

Конфигурация хранится в YAML и описывает git-репозиторий со спецификациями и локальный путь для их сохранения.

---

## Модель

```python
from swax.config import Config, GitConfig, SpecsConfig

config = Config(
    git=GitConfig(url="https://github.com/org/api-specs.git", location="specs/"),
    specs=SpecsConfig(type="openapi", location="specs/"),
)
```

Поле `specs.type` — объявление формата (`"swagger"` или `"openapi"`); реальный парсер (Prance) определяет версию автоматически, поэтому значение носит информационный характер.

---

## Сохранение после инициализации

`run_init` создаёт конфигурацию из ответов пользователя и сохраняет её:

```python
from pathlib import Path

from swax.config import Config, GitConfig, SpecsConfig, save_config

def persist_config(repo_url: str, specs_location: str, download_path: Path, project_root: Path) -> None:
    config = Config(
        git=GitConfig(url=repo_url, location=specs_location),
        specs=SpecsConfig(type="openapi", location=str(download_path)),
    )
    save_config(config, project_root / ".swax" / "config.yml")
```

`save_config` создаёт родительские каталоги и пишет детерминированный YAML — diff между запусками стабилен.

---

## Чтение перед построением графа

`run_discover` читает конфигурацию, чтобы узнать, где лежат локальные спецификации:

```python
from swax.config import load_config

def locate_specs(project_root: Path) -> Path:
    config = load_config(project_root / ".swax" / "config.yml")
    return project_root / config.specs.location
```

Файл конфигурации обязан существовать к моменту `discover` — `init` должен быть запущен ранее.
```

#### .usages file: `swax/config/.usages/environment.md`

```md
# Environment — `.env` and `SWAX_*` variables

## Предметная область

Шаблоны загрузки `.env` и валидации переменных окружения `SWAX_*`. Целевая аудитория: cell `swax/cli/` (точка входа CLI загружает `.env` перед выполнением команд) и cell-ы, которым нужны креды LLM (`applications/discover/`, `swax/llm/`).

Все переменные имеют префикс `SWAX_`. Файл `.env` загружается опционально — реальные переменные окружения имеют приоритет.

---

## Обязательные переменные

| Variable | Назначение |
|----------|-----------|
| `SWAX_LLM_PROTOCOL` | `"anthropic"` или `"openai"` |
| `SWAX_LLM_BASE_URL` | базовый URL **без** версионного сегмента (`/v1`) |
| `SWAX_LLM_TOKEN` | токен доступа к LLM API |

---

## Загрузка `.env`

Выполнять рано — в callback группы Click, до подкоманд:

```python
from pathlib import Path

from swax.config import load_env

def setup_cli(env_file: Path) -> None:
    load_env(env_file)
```

`load_env` использует `override=False`: переменные, уже заданные в shell, не перезаписываются. Это позволяет разработчикам и CI переопределять значения без редактирования `.env`.

---

## Ленивая валидация

`require_vars()` возвращает mapping только если все обязательные переменные присутствуют; иначе выбрасывает `MissingEnvironmentVariablesError`. Вызывать лениво — только в use-case-ах, которым нужен LLM:

```python
from swax.config import require_vars

def before_llm_call() -> dict[str, str]:
    return require_vars()
```

`init` не нуждается в кредах LLM и не должен вызывать `require_vars`.

---

## Валидаторы значений

`parse_protocol` и `parse_base_url` проверяют формат значений до конструирования SDK-клиентов:

```python
from swax.config import parse_protocol, parse_base_url

protocol = parse_protocol(os.environ["SWAX_LLM_PROTOCOL"])
base_url = parse_base_url(os.environ["SWAX_LLM_BASE_URL"])
```

Оба выбрасывают доменные исключения (`InvalidLLMProtocolError`, `InvalidLLMBaseURLError`) с понятным сообщением, которое CLI маппит в `click.ClickException`.

---

## Тестирование

В тестах задавать переменные через `monkeypatch.setenv` и удалять через `monkeypatch.delenv` — не писать файлы `.env`.
```

---

### Cell 2/12: `swax/fs/` (created anew)

#### CODEMANIFEST: `swax/fs/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  
  Use relative imports inside the cell.
  Use `pathlib.Path` for all filesystem paths.
  In tests, exercise filesystem operations through `tmp_path` only — no real project directories.

---

"ensure_swax_dir(project_root: pathlib.Path) -> swax_dir: pathlib.Path":
  location: ensure_swax_dir.py
  annotations: |
    Guarantee the `.swax/` directory exists under the project root and return its path.
    
    `project_root`: root of the Swax project (where `.swax/` lives).
    `swax_dir`: the `.swax/` directory path, ready for `config.yml` and `traceability.yml` writes.
    
    Algorithm:
    1. Resolve `.swax` as a subdirectory of `project_root`.
    2. Create it with `mkdir(parents=True, exist_ok=True)`.
    3. Return the resolved path.
    
    Requirements:
    - Idempotent — safe to call before every write operation.

"copy_specs(source: pathlib.Path, destination: pathlib.Path) -> None":
  location: copy_specs.py
  annotations: |
    Copy downloaded specifications from the temporary clone directory into the local project path.
    
    `source`: directory of specs inside the cloned repository (yielded by `clone_specs`).
    `destination`: local download path declared in `SpecsConfig.location`.
    
    Algorithm:
    1. Create `destination` parents if missing.
    2. Recursively copy `source` into `destination` via `shutil.copytree(..., dirs_exist_ok=True)`.
    
    Requirements:
    - Must overwrite existing files on re-runs (re-running `init` updates local specs).
    - Preserve directory structure of the source.
    
    Constraints:
    - Do not follow symlinks in the clone — copy their targets as regular files.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Filesystem operations for the Swax project layout (`.swax/` directory and spec copying).
```

#### .usages file: `swax/fs/.usages/project-layout.md`

```md
# Project layout — `.swax/` directory and spec copying

## Предметная область

Шаблоны управления файловой структурой проекта Swax. Целевая аудитория: cell `applications/init/` (создаёт структуру и копирует спецификации после клонирования).

Структура проекта Swax на файловой системе:
```
<project_root>/
├── .swax/
│   ├── config.yml          # создастся через `save_config`
│   └── traceability.yml    # создастся позже через `save_traceability`
└── <specs.location>/       # сюда попадут спецификации через `copy_specs`
    └── *.yaml | *.json
```

---

## Гарантия каталога `.swax/`

Вызывать перед каждой записью в `.swax/` — idempotent:

```python
from pathlib import Path

from swax.fs import ensure_swax_dir

def write_config(project_root: Path) -> Path:
    swax_dir = ensure_swax_dir(project_root)
    config_path = swax_dir / "config.yml"
    # save_config(config, config_path) — делегируется cell `config/`
    return config_path
```

`ensure_swax_dir` создаёт `.swax/` с `parents=True, exist_ok=True` — безопасно вызывать повторно.

---

## Копирование спецификаций

После клонирования репозитория через `clone_specs` (cell `git/`) спецификации нужно перенести в локальный путь проекта. Путь назначения берётся из `SpecsConfig.location`:

```python
from pathlib import Path

from swax.fs import copy_specs

def install_specs(specs_in_clone: Path, download_path: Path) -> None:
    copy_specs(source=specs_in_clone, destination=download_path)
```

Соглашения потребителя:
- `source` — путь, yields из `clone_specs` (временный каталог клонирования).
- `destination` — локальный путь из `SpecsConfig.location`. Cell `fs/` создаёт родительские каталоги при необходимости.
- Повторный запуск `init` перезаписывает существующие файлы (обновление локальных спецификаций).
```

---

### Cell 3/12: `swax/git/` (created anew)

#### CODEMANIFEST: `swax/git/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md
  gitpython: .goga/usages/cooks/gitpython.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `gitpython` for repository cloning and error mapping.
  
  Use relative imports inside the cell.
  Swax treats the source repository as read-only — clone, read, delete. No commits, no pushes.

---

"clone_specs(repo_url: str, specs_location: str) -> Iterator[specs_path: pathlib.Path]":
  location: clone_specs.py
  annotations: |
    Clone the remote repository into a temporary directory and yield the path to the specs subdirectory for the duration of the `with` block. Cleanup is guaranteed even on exception.
    
    `repo_url`: clone URL of the repository holding the API specifications.
    `specs_location`: subdirectory inside the repo where specs live.
    `specs_path`: resolved path to the specs directory inside the clone, valid only inside the context.
    
    Algorithm:
    1. Enter a `TemporaryDirectory(prefix="swax-")` context manager.
    2. Call `Repo.clone_from(repo_url, tmp.name, depth=1)` for a shallow clone.
    3. Resolve `tmp.name / specs_location`.
    4. If the resolved path does not exist, raise `SpecsNotFoundError`.
    5. `yield` the resolved path.
    6. On exit (normal or exception), `TemporaryDirectory` cleans up automatically.
    
    Requirements:
    - Use `depth=1` — only the latest commit is needed.
    - Wrap `GitCommandError` into `RepositoryCloneError` carrying `repo_url` and the original reason.
    
    Constraints:
    - Do not embed credentials in `repo_url` — rely on git credential helpers for private repositories.
    - Do not return a path that outlives the context — the temporary directory is deleted on exit.
    
    Use `gitpython` for the cloning and cleanup patterns.

"RepositoryCloneError(url: str, reason: str)":
  location: errors.py
  annotations: |
    Raised by `clone_specs` when GitPython fails to clone the repository.
    
    `url`: the clone URL that failed, surfaced to the user.
    `reason`: the original error message from GitPython.

"SpecsNotFoundError(path: pathlib.Path)":
  location: errors.py
  annotations: |
    Raised by `clone_specs` when the declared `specs_location` does not exist inside the cloned repository.
    
    `path`: the expected path that was not found.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Git repository cloning for reading API specifications (read-only access pattern).
```

#### .usages file: `swax/git/.usages/specs-repository.md`

```md
# Specs repository — клонирование для чтения спецификаций

## Предметная область

Шаблоны доступа к удалённому git-репозиторию со спецификациями OpenAPI/Swagger. Целевая аудитория: cell `applications/init/` (клонирует репозиторий, чтобы скопировать спецификации в локальный путь проекта).

Swax обращается с репозиторием как с read-only: клонирует, читает, удаляет временный клон. Никаких commit-ов и push-ей.

---

## Клонирование как context manager

`clone_specs` — это context manager: yields путь к спецификациям внутри временного клона и автоматически очищает временный каталог при выходе (нормальном или с исключением):

```python
from pathlib import Path

from swax.git import clone_specs

def install_specs(repo_url: str, specs_location: str) -> Path:
    with clone_specs(repo_url, specs_location) as specs_path:
        # specs_path валиден только внутри with — после выхода каталог удалён
        # copy_specs(source=specs_path, destination=local_path) — делегируется cell `fs/`
        return list(specs_path.rglob("*.yaml"))
```

Соглашения потребителя:
- `repo_url` — clone URL. Для приватных репозиториев полагаться на git credential helpers; не встраивать токены в URL.
- `specs_location` — подкаталог в репозитории, где лежат спецификации (из `GitConfig.location`).
- Использовать `with` обязательно — path за пределами блока невалиден.

---

## Обработка доменных исключений

`clone_specs` выбрасывает два доменных исключения. Потребитель (CLI-handler команды `init`) маппит их в `click.ClickException` для единообразного выхода:

```python
from swax.git import clone_specs, RepositoryCloneError, SpecsNotFoundError

def safe_clone(repo_url: str, specs_location: str):
    try:
        with clone_specs(repo_url, specs_location) as specs_path:
            yield specs_path
    except RepositoryCloneError as exc:
        # click.ClickException(f"Не удалось клонировать {exc.url}: {exc.reason}")
        ...
    except SpecsNotFoundError as exc:
        # click.ClickException(f"Спецификации не найдены в {exc.path}")
        ...
```

`RepositoryCloneError` несёт `url` и `reason` — для понятного сообщения пользователю.
`SpecsNotFoundError` несёт `path` — указывает, какой подкаталог отсутствует в репозитории.

---

## Тестирование

В тестах `mock.patch` вызова `Repo.clone_from` в точке импорта (conventions — Моки). Не выполнять реальное клонирование в тестах.
```

---

### Cell 4/12: `swax/openapi/` (created anew)

#### CODEMANIFEST: `swax/openapi/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md
  prance: .goga/usages/cooks/prance.md
  pyyaml: .goga/usages/cooks/pyyaml.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `prance` for resolving parser and path/schema extraction.
  Use `pyyaml` for the lightweight spec-detection heuristic in `discover_specs`.
  
  Use relative imports inside the cell.
  The traceability graph operates on paths only — no HTTP methods, no resource abstraction (architectural rule: minimal abstraction).
  Swagger 2.0 and OpenAPI 3.x are handled transparently — both store paths under `paths`.

---

"parse_spec(spec_path: pathlib.Path) -> spec: dict":
  location: parse_spec.py
  annotations: |
    Parse a single specification file into a fully dereferenced dict via Prance.
    
    `spec_path`: path to a `.yaml`, `.yml`, or `.json` spec file.
    `spec`: resolved specification with `$ref` inlined; contains `paths` and schemas.
    
    Algorithm:
    1. Construct `ResolvingParser(str(spec_path), backend="openapi-spec-validator", strict=False, resolve_types=True)`.
    2. Return `parser.specification`.
    3. On any exception from Prance, raise `SpecParseError` carrying `spec_path` and the original reason.
    
    Requirements:
    - `$ref` must be resolved in memory — downstream code never resolves references manually.
    
    Constraints:
    - RAM usage scales with spec size and reference count (known limitation — accept it).
    
    Use `prance` for the resolving parser pattern.

"extract_paths(spec: dict) -> paths: list[str]":
  location: extract_paths.py
  annotations: |
    Collect API path templates from a parsed specification, discarding HTTP methods.
    
    `spec`: dereferenced specification dict (output of `parse_spec`).
    `paths`: sorted list of path templates (e.g. `/users`, `/users/{id}`).
    
    Algorithm:
    1. Read `spec.get("paths", {})`.
    2. Return `sorted(keys)`.
    
    Requirements:
    - Result feeds the traceability graph nodes directly — no method-level entries.
    
    Use `prance` for the path extraction pattern.

"extract_schemas(spec: dict) -> schemas: dict":
  location: extract_schemas.py
  annotations: |
    Collect schema definitions from a parsed specification for LLM context enrichment.
    
    `spec`: dereferenced specification dict.
    `schemas`: mapping of schema name to its definition (already inlined by Prance).
    
    Algorithm:
    1. If `spec` has `components`, return `spec["components"].get("schemas", {})` (OpenAPI 3.x).
    2. Otherwise return `spec.get("definitions", {})` (Swagger 2.0).
    
    Requirements:
    - Schemas are used only by `build_refine_user_prompt` for ambiguous-pair clarification — never stored in the traceability graph.
    
    Use `prance` for the version-aware schema extraction pattern.

"discover_specs(root: pathlib.Path) -> specs: list[pathlib.Path]":
  location: discover_specs.py
  annotations: |
    Enumerate spec files under `root` by extension and a lightweight content heuristic.
    
    `root`: directory to search (typically the local specs location from `SpecsConfig`).
    `specs`: sorted list of spec file paths.
    
    Algorithm:
    1. `rglob("*")` under `root`.
    2. Keep files whose suffix is in `(".yaml", ".yml", ".json")`.
    3. For each candidate, `yaml.safe_load` the head and keep only dicts containing `openapi` or `swagger`.
    4. Return the sorted list.
    
    Requirements:
    - The heuristic must be cheap — full parsing happens later via `parse_spec`.
    - Use `yaml.safe_load` for the head check only.
    
    Use `prance` for the discovery pattern.
    Use `pyyaml` for the safe_load usage.

"SpecParseError(path: pathlib.Path, reason: str)":
  location: errors.py
  annotations: |
    Raised by `parse_spec` when Prance fails to parse or dereference a specification.
    
    `path`: the offending spec file path, surfaced to the user.
    `reason`: the original error message from Prance.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  OpenAPI/Swagger parsing via Prance and extraction of paths and schemas for the traceability graph.
```

#### .usages file: `swax/openapi/.usages/parsing.md`

```md
# Parsing — разбор спецификаций OpenAPI/Swagger

## Предметная область

Шаблоны обнаружения файлов спецификаций и их разбора в полностью разыменованный dict. Целевая аудитория: cell `applications/discover/` (находит все спецификации в локальном каталоге и разбирает каждую через Prance).

Prance разворачивает `$ref` в памяти, поэтому последующему коду никогда не приходится разрешать ссылки вручную. Swagger 2.0 и OpenAPI 3.x обрабатываются прозрачно.

---

## Обнаружение спецификаций

`discover_specs` сканирует каталог по расширению и лёгкой эвристике (файл должен содержать ключ `openapi` или `swagger` в начале):

```python
from pathlib import Path

from swax.openapi import discover_specs

def collect_spec_files(specs_root: Path) -> list[Path]:
    return discover_specs(specs_root)
```

Соглашения потребителя:
- `root` — локальный путь из `SpecsConfig.location`.
- Эвристика дешёвая (читает только head файла) — полный разбор выполняется позже через `parse_spec`.
- Возвращает отсортированный список для детерминированного порядка обработки.

---

## Разбор спецификации

`parse_spec` возвращает полностью разырешённый dict — `$ref` уже инлайнены:

```python
from pathlib import Path

from swax.openapi import parse_spec

def load_one_spec(spec_path: Path) -> dict:
    return parse_spec(spec_path)
```

Соглашения потребителя:
- Принимает `.yaml`, `.yml`, `.json` файлы.
- Возвращает dict с `paths` (пути) и схемами (в `components.schemas` для OpenAPI 3.x или `definitions` для Swagger 2.0).
- При ошибке разбора выбрасывает `SpecParseError` с путём файла и причиной — CLI-handler маппит в `click.ClickException`.

---

## Объединение: сканирование → разбор

Типичный сценарий в use-case:

```python
from swax.openapi import discover_specs, parse_spec

def load_all_specs(specs_root: Path) -> list[dict]:
    return [parse_spec(p) for p in discover_specs(specs_root)]
```

RAM-ограничение: Prance разворачивает `$ref` в памяти, поэтому для очень больших спецификаций потребление RAM может быть значительным — известное ограничение, принимается архитектурно.
```

#### .usages file: `swax/openapi/.usages/extraction.md`

```md
# Extraction — пути и схемы из разобранной спецификации

## Предметная область

Шаблоны извлечения данных из разобранной спецификации для построения графа отслеживаемости. Целевая аудитория: cell `applications/discover/` (собирает узлы графа из путей и готовит схемы для уточняющего LLM-прохода).

Граф отслеживаемости оперирует только путями — без HTTP-методов, без абстракции ресурсов. Это архитектурное правило Swax: минимальная абстракция.

---

## Извлечение путей (узлы графа)

`extract_paths` возвращает отсортированный список путей API из разобранной спецификации:

```python
from swax.openapi import extract_paths

def collect_nodes(spec: dict) -> list[str]:
    return extract_paths(spec)
```

Соглашения потребителя:
- `spec` — вывод `parse_spec` (dereferenced dict).
- Возвращает шаблоны путей (например, `/users`, `/users/{id}`).
- Результат напрямую становится узлами графа отслеживаемости — методов в графе нет.

---

## Извлечение схем (контекст для LLM)

`extract_schemas` возвращает определения схем для уточняющего LLM-прохода. Функция автоматически различает OpenAPI 3.x (`components.schemas`) и Swagger 2.0 (`definitions`):

```python
from swax.openapi import extract_schemas

def collect_schema_context(spec: dict) -> dict:
    return extract_schemas(spec)
```

Соглашения потребителя:
- Схемы используются ТОЛЬКО в `build_refine_user_prompt` (cell `prompts/`) для уточнения неоднозначных пар зависимостей.
- Схемы НИКОГДА не сохраняются в граф отслеживаемости — граф хранит только пути.

---

## Полный сценарий извлечения

```python
from swax.openapi import extract_paths, extract_schemas

def extract_graph_input(spec: dict) -> tuple[list[str], dict]:
    return extract_paths(spec), extract_schemas(spec)
```

Use-case `run_discover` агрегирует пути всех спецификаций в единый список узлов, а схемы передаёт в уточняющий промпт при необходимости.
```

---

### Cell 5/12: `swax/traceability/` (created anew)

#### CODEMANIFEST: `swax/traceability/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md
  pyyaml: .goga/usages/cooks/pyyaml.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `pyyaml` for serialization of the graph to `.swax/traceability.yml`.
  
  All pydantic models use `kw_only=True`.
  Use relative imports inside the cell.
  The traceability graph stores paths only — no HTTP methods, no resource abstraction.
  Edge deduplication is mandatory before saving (Acceptance Criterion #8).

---

"TraceabilityGraph(edges: dict[str, list[str]])":
  location: TraceabilityGraph.py
  annotations: |
    In-memory model of the traceability graph: API path → list of dependent paths.
    
    `edges`: mapping of source path to its dependencies. Defaults to empty dict.
    
    Use `conventions` for pydantic model rules.
    
    Requirements:
    - Accumulates edges during `run_discover` via `add_edge`.
    - Caller invokes `deduplicate` before saving to remove duplicate edges.
  properties:
    "edges -> dict[str, list[str]]": |
      The underlying adjacency mapping. Exposed for serialization; consumers mutate it via `add_edge`, not by direct assignment.
  methods:
    "add_edge(source: str, target: str) -> None": |
      Record a single dependency: `source` depends on `target`.
      
      `source`: the path that depends on another.
      `target`: the path it depends on.
      
      Algorithm:
      1. Append `target` to `edges.setdefault(source, [])`.
      
      Requirements:
      - Permits duplicates at insert time — resolved later via `deduplicate`.
      - Self-loops (`source == target`) are permitted at insert time, filtered out by `deduplicate`.
    "deduplicate() -> None": |
      Remove duplicate edges and self-loops in-place, preparing the graph for deterministic serialization.
      
      Algorithm:
      1. For each key in `edges`, replace its list with `sorted(set(list))`.
      2. Remove the key from its own list (no self-dependencies).
      
      Requirements:
      - Idempotent — safe to call multiple times.
      - Returns sorted lists for stable dump.

"load_traceability(path: pathlib.Path) -> graph: TraceabilityGraph":
  location: storage.py
  annotations: |
    Read `.swax/traceability.yml` into a `TraceabilityGraph`.
    
    `path`: path to the traceability file.
    `graph`: the loaded graph model.
    
    Algorithm:
    1. Read file text as UTF-8.
    2. `yaml.safe_load` the contents.
    3. Coerce each value to `list(v)` for normalization.
    4. `TraceabilityGraph(edges=normalized)`.
    
    Requirements:
    - Use `yaml.safe_load` only.
    - An empty file yields an empty graph, not an error.
    
    Use `pyyaml` for the loading pattern.

"save_traceability(graph: TraceabilityGraph, path: pathlib.Path) -> None":
  location: storage.py
  annotations: |
    Persist `TraceabilityGraph` to `.swax/traceability.yml` deterministically.
    
    `graph`: the graph to write (caller must have called `deduplicate` first).
    `path`: destination file path.
    
    Algorithm:
    1. `graph.model_dump(mode="json")` for YAML-safe primitives.
    2. Create parent directories.
    3. Sort keys and values explicitly: `{k: sorted(v) for k, v in sorted(payload["edges"].items())}`.
    4. `yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False)`.
    5. Write text as UTF-8.
    
    Requirements:
    - Output must be stable across runs — deterministic order of keys and values.
    - Sort in Python explicitly, do not rely on yaml `sort_keys=True`.
    
    Use `pyyaml` for the dumping pattern.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Traceability graph model and YAML persistence (paths-only, deterministic serialization).
```

#### .usages file: `swax/traceability/.usages/graph-lifecycle.md`

```md
# Traceability graph — жизненный цикл и персистентность

## Предметная область

Шаблоны построения и сохранения графа отслеживаемости API. Целевая аудитория: cell `applications/discover/` (накапливает рёбра из LLM-вывода и сохраняет граф в `.swax/traceability.yml`).

Граф оперирует только путями — без HTTP-методов, без абстракции ресурсов. Это архитектурное правило Swax: минимальная абстракция. Узлы = пути API, рёбра = выявленные зависимости между эндпоинтами.

Формат файла `.swax/traceability.yml`:
```yaml
/payment:
  - /users
  - /orders
/orders:
  - /payment
```
Ключи — пути, значения — списки зависимых путей.

---

## Построение графа

`TraceabilityGraph` накапливает рёбра через `add_edge` во время LLM-анализа:

```python
from swax.traceability import TraceabilityGraph

def build_from_llm_output(dependencies: dict[str, list[str]]) -> TraceabilityGraph:
    graph = TraceabilityGraph(edges={})
    for source, targets in dependencies.items():
        for target in targets:
            graph.add_edge(source=source, target=target)
    return graph
```

Соглашения потребителя:
- `source` — путь, который зависит от другого.
- `target` — путь, от которого зависит `source`.
- Дубликаты в момент добавления допустимы — они устраняются позже через `deduplicate`.

---

## Дедупликация перед сохранением

Перед сериализацией граф обязательно дедуплицируется — это убирает повторяющиеся рёбра и самозависимости, обеспечивая детерминированный вывод:

```python
from swax.traceability import TraceabilityGraph

def finalize(graph: TraceabilityGraph) -> TraceabilityGraph:
    graph.deduplicate()
    return graph
```

Соглашения потребителя:
- Идемпотентен — безопасно вызывать несколько раз.
- Возвращает отсортированные списки рёбер внутри каждого ключа.

---

## Сохранение графа

`save_traceability` пишет детерминированный YAML: ключи и значения отсортированы явно в Python для стабильного diff-а между запусками:

```python
from pathlib import Path

from swax.traceability import TraceabilityGraph, save_traceability

def persist(graph: TraceabilityGraph, project_root: Path) -> None:
    save_traceability(graph, project_root / ".swax" / "traceability.yml")
```

Соглашения потребителя:
- Передать граф, для которого уже вызван `deduplicate`.
- Функция создаёт родительские каталоги при необходимости.
- `mode="json"` для pydantic-dump гарантирует YAML-совместимые примитивы.

---

## Чтение графа

`load_traceability` читает `.swax/traceability.yml` обратно в модель. Пустой файл даёт пустой граф, а не ошибку:

```python
from pathlib import Path

from swax.traceability import load_traceability

def reload(project_root: Path):
    return load_traceability(project_root / ".swax" / "traceability.yml")
```

Чтение используется в задачах 2-3 (plan, update) — задача 1 (discover) только пишет граф.
```

---

### Cell 6/12: `swax/prompts/` (created anew)

#### CODEMANIFEST: `swax/prompts/CODEMANIFEST`

```yaml
Usages:
  conventions: .goga/usages/conventions.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  
  Use relative imports inside the cell.
  Every routine returns a fully-formed prompt string ready for `LLMClient.ask` / `ask_multi_turn`.
  Prompts must request structured JSON output — the consumer parses the response defensively (see risk: LLM output quality).
  Prompts must not embed filesystem paths, tokens, or secrets — only the data passed as arguments.

---

"build_graph_system_prompt() -> prompt: str":
  location: build_graph_system_prompt.py
  annotations: |
    Construct the system prompt that instructs the LLM to act as an API dependency analyst.
    
    `prompt`: the system message reused across both passes of `run_discover`.
    
    Requirements:
    - Define the LLM role: analyze API endpoints and propose dependency edges between paths.
    - Mandate the output contract: a JSON object mapping source path to list of dependent paths.
    - Forbid prose around JSON — response must be parseable by `json.loads`.
    - State explicitly that the graph operates on paths only — no HTTP methods.
    
    Constraints:
    - No parameters — the system prompt is constant for the discover use-case.
    - No endpoint list, no schemas — those go into user prompts.

"build_graph_user_prompt(endpoints: list[str]) -> prompt: str":
  location: build_graph_user_prompt.py
  annotations: |
    Construct the first-pass user prompt: list endpoints and ask for dependency hypotheses.
    
    `endpoints`: API path templates collected by `extract_paths` across all parsed specs.
    `prompt`: the user message for the initial `LLMClient.ask` call.
    
    Algorithm:
    1. Render the endpoint list as a JSON array under an `endpoints` key.
    2. Instruct the LLM to return only a JSON object `{source_path: [dependent_paths]}`.
    3. Allow the LLM to flag uncertain pairs in the response so the consumer can route them to the refine pass.
    
    Requirements:
    - Output format must match what the consumer's JSON parser expects.
    - Endpoint order in the prompt must follow the sorted order from `extract_paths` for determinism.
    
    Constraints:
    - Do not inline schemas here — they belong to the refine pass.

"build_refine_user_prompt(ambiguous_pairs: list[str], schemas: dict) -> prompt: str":
  location: build_refine_user_prompt.py
  annotations: |
    Construct the refine-pass user prompt: provide schemas for ambiguous pairs and ask for final dependency decisions.
    
    `ambiguous_pairs`: pairs flagged as uncertain from the first-pass response (e.g. `"/users -> /orders"`).
    `schemas`: schema definitions from `extract_schemas`, included as context.
    `prompt`: the user message for the final turn of `LLMClient.ask_multi_turn`.
    
    Algorithm:
    1. Render `ambiguous_pairs` as a JSON array.
    2. Render `schemas` as a JSON object keyed by schema name.
    3. Instruct the LLM to return a consolidated JSON object `{source_path: [dependent_paths]}` covering all pairs.
    4. Forbid introducing paths outside the provided endpoint universe.
    
    Requirements:
    - Only schemas relevant to the ambiguous pairs should influence the answer — pass the full dict, the LLM selects.
    - Output contract identical to `build_graph_user_prompt` so the consumer reuses the same parser.
    
    Constraints:
    - Do not re-list all endpoints — the multi-turn context already carries them.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  LLM prompt builders for the two-pass traceability graph construction scenario.
```

#### .usages file: `swax/prompts/.usages/traceability-llm-prompts.md`

```md
# Traceability LLM prompts — сборка промптов для построения графа

## Предметная область

Шаблоны сборки промптов для LLM-анализа зависимостей API. Целевая аудитория: cell `applications/discover/` (использует три промпт-билдера в двухпроходном сценарии построения графа отслеживаемости).

Cell собирает строки промптов — сами вызовы LLM и парсинг JSON выполняются потребителем через `LLMClient` (cell `llm/`). Это разделение ответственности: prompts/ знает «что сказать LLM», llm/ знает «как вызвать API».

---

## System-промпт аналитика

`build_graph_system_prompt` возвращает константный system-промпт, переиспользуемый в обоих проходах:

```python
from swax.prompts import build_graph_system_prompt

def setup_llm_context() -> str:
    return build_graph_system_prompt()
```

Соглашения потребителя:
- Без параметров — системный промпт постоянен для use-case-а discover.
- Передаётся как `system=` в `LLMClient.ask` / `ask_multi_turn`.
- Запрашивает JSON-объект `{source_path: [dependent_paths]}` без prose-обёртки.

---

## Первый проход: гипотезы зависимостей

`build_graph_user_prompt` формирует user-сообщение с полным списком эндпоинтов:

```python
from swax.prompts import build_graph_user_prompt

def first_pass(endpoints: list[str]) -> str:
    return build_graph_user_prompt(endpoints)
```

Соглашения потребителя:
- `endpoints` — пути API из `extract_paths` (cell `openapi/`), отсортированные.
- LLM возвращает гипотезы зависимостей и может помечать неуверенные пары для уточняющего прохода.
- Потребитель парсит JSON защитно (через `json.loads` с обработкой `JSONDecodeError`).

---

## Уточняющий проход: схемы для неоднозначных пар

`build_refine_user_prompt` формирует user-сообщение для второго (multi-turn) хода — со схемами неоднозначных пар:

```python
from swax.prompts import build_refine_user_prompt

def refine_pass(ambiguous_pairs: list[str], schemas: dict) -> str:
    return build_refine_user_prompt(ambiguous_pairs, schemas)
```

Соглашения потребителя:
- `ambiguous_pairs` — пары, помеченные LLM как неуверенные в первом проходе (например, `"/users -> /orders"`).
- `schemas` — словарь схем из `extract_schemas` (cell `openapi/`).
- Используется в `LLMClient.ask_multi_turn` — multi-turn context уже несёт первый ход.
- Выходной JSON-контракт идентичен первому проходу — потребитель переиспользует тот же парсер.

---

## Полный сценарий двух проходов

use-case `run_discover` собирает все три промпта в один сценарий:

```python
from swax.prompts import (
    build_graph_system_prompt,
    build_graph_user_prompt,
    build_refine_user_prompt,
)

def run_two_pass_analysis(endpoints, ambiguous_pairs, schemas, llm_client):
    system = build_graph_system_prompt()
    first_user = build_graph_user_prompt(endpoints)
    raw_first = llm_client.ask(system=system, user=first_user)
    # ... parse raw_first, collect ambiguous_pairs ...
    
    refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)
    raw_refined = llm_client.ask_multi_turn(
        system=system,
        messages=[
            {"role": "user", "content": first_user},
            {"role": "assistant", "content": raw_first},
            {"role": "user", "content": refine_user},
        ],
    )
    return raw_refined
```

Потребитель сам управляет маппингом ошибок LLM (`LLMCallError`, `LLMRateLimitedError`) и парсингом JSON — это не ответственность cell-а `prompts/`.
```

---

### Cell 7/12: `swax/llm/` (created anew)

#### CODEMANIFEST: `swax/llm/CODEMANIFEST`

```yaml
Imports:
  - Types:
      - require_vars
      - MissingEnvironmentVariablesError
    Usages:
      - environment
    From: swax/config

Usages:
  conventions: .goga/usages/conventions.md
  anthropic: .goga/usages/cooks/anthropic.md
  openai: .goga/usages/cooks/openai.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `anthropic` for SDK client and Anthropic error mapping.
  Use `openai` for SDK client and OpenAI error mapping.
  Use `environment` from Imports to obtain `require_vars` before constructing clients.
  
  Use relative imports inside the cell.
  `SWAX_LLM_TOKEN` must never appear in logs.
  Adapters receive the SDK client via constructor injection — for testability via mock at import point.
  DEFAULT_MODEL is fixed in code per adapter.

---

"LLMClient()":
  location: LLMClient.py
  annotations: |
    Structural protocol for LLM transports. Adapters satisfy the protocol implicitly — no inheritance required.
    
    The protocol is domain-agnostic: methods accept pre-built system/user strings and return raw response text. Multi-step orchestration (dependency inference, schema refinement) lives in the consumer, not here.
    
    Use `conventions` for typing rules.
  methods:
    "ask(system: str, user: str) -> str": |
      Single-turn transport: send one system + one user message, return raw response text.
      
      `system`: the system prompt (output of `build_graph_system_prompt`).
      `user`: the user payload (output of `build_graph_user_prompt` or `build_refine_user_prompt`).
      
      Requirements:
      - Return the concatenated text content of the response.
      - Map SDK errors to `LLMCallError` / `LLMRateLimitedError`.
    "ask_multi_turn(system: str, messages: list[dict[str, str]]) -> str": |
      Multi-turn transport: send a system prompt plus an ordered message history, return raw response text.
      
      `system`: the system prompt reused across turns.
      `messages`: ordered list of `{"role": ..., "content": ...}` dicts for the refinement pass.
      
      Requirements:
      - Preserve message order — the SDK relies on it for context continuity.
      - Map SDK errors to `LLMCallError` / `LLMRateLimitedError`.

"LLMClient::AnthropicAdapter(client: Anthropic)":
  location: AnthropicAdapter.py
  annotations: |
    `LLMClient` implementation backed by the Anthropic SDK.
    
    `client`: injected `Anthropic` SDK client, constructed by `build_anthropic_client`.
    
    Use `anthropic` for the SDK call patterns and error mapping.
    Use `conventions` for typing and docstring rules.
    
    Requirements:
    - Methods must match `LLMClient` signatures exactly — provider switching requires no code change.
  properties:
    "client -> Anthropic": |
      The injected Anthropic SDK client instance.
  methods:
    "ask(system: str, user: str) -> str": |
      Anthropic-backed single-turn call.
      
      Algorithm:
      1. Call `client.messages.create(model=DEFAULT_MODEL, max_tokens=4096, system=system, messages=[{"role": "user", "content": user}])`.
      2. Concatenate `block.text` for blocks where `block.type == "text"`.
      3. On `RateLimitError`, raise `LLMRateLimitedError`.
      4. On `APIError`, raise `LLMCallError`.
      
      Use `anthropic` for the call and error mapping pattern.
    "ask_multi_turn(system: str, messages: list[dict[str, str]]) -> str": |
      Anthropic-backed multi-turn call.
      
      Algorithm:
      1. Call `client.messages.create(model=DEFAULT_MODEL, max_tokens=4096, system=system, messages=messages)`.
      2. Concatenate `block.text` for blocks where `block.type == "text"`.
      3. Map errors as in `ask`.
      
      Use `anthropic` for the multi-turn call pattern.

"LLMClient::OpenAIAdapter(client: OpenAI)":
  location: OpenAIAdapter.py
  annotations: |
    `LLMClient` implementation backed by the OpenAI SDK.
    
    `client`: injected `OpenAI` SDK client, constructed by `build_openai_client`.
    
    Use `openai` for the SDK call patterns and error mapping.
    Use `conventions` for typing and docstring rules.
    
    Requirements:
    - Methods must match `LLMClient` signatures exactly — provider switching requires no code change.
  properties:
    "client -> OpenAI": |
      The injected OpenAI SDK client instance.
  methods:
    "ask(system: str, user: str) -> str": |
      OpenAI-backed single-turn call.
      
      Algorithm:
      1. Call `client.chat.completions.create(model=DEFAULT_MODEL, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])`.
      2. Return `response.choices[0].message.content or ""`.
      3. On `RateLimitError`, raise `LLMRateLimitedError`.
      4. On `APIError`, raise `LLMCallError`.
      
      Use `openai` for the call and error mapping pattern.
    "ask_multi_turn(system: str, messages: list[dict[str, str]]) -> str": |
      OpenAI-backed multi-turn call.
      
      Algorithm:
      1. Prepend `{"role": "system", "content": system}` to `messages`.
      2. Call `client.chat.completions.create(model=DEFAULT_MODEL, messages=prepended)`.
      3. Return `response.choices[0].message.content or ""`.
      4. Map errors as in `ask`.
      
      Use `openai` for the multi-turn call pattern.

"LLMCallError(reason: str)":
  location: errors.py
  annotations: |
    Raised by adapters when a generic LLM API error occurs (non-rate-limit).
    
    `reason`: the original error message from the SDK.

"LLMRateLimitedError(reason: str)":
  location: errors.py
  annotations: |
    Raised by adapters when the LLM API returns a rate-limit error.
    
    `reason`: the original error message from the SDK.

"UnsupportedLLMProtocolError(protocol: str)":
  location: errors.py
  annotations: |
    Raised by `build_llm_client` when `SWAX_LLM_PROTOCOL` is neither `"anthropic"` nor `"openai"`.
    
    `protocol`: the offending value submitted by the user.

"build_anthropic_client() -> client: Anthropic":
  location: build_anthropic_client.py
  annotations: |
    Construct an Anthropic SDK client from `SWAX_LLM_*` environment variables.
    
    `client`: ready-to-use `Anthropic` instance for `AnthropicAdapter`.
    
    Algorithm:
    1. Call `require_vars` to fail fast on missing credentials.
    2. Read `SWAX_LLM_TOKEN` and `SWAX_LLM_BASE_URL` from `os.environ`.
    3. Construct `Anthropic(api_key=token, base_url=base_url)`.
    
    Requirements:
    - Never hardcode credentials.
    - Base URL must already be validated (no `/v1`) — see `environment` from Imports.
    
    Use `anthropic` for the client construction pattern.

"build_openai_client() -> client: OpenAI":
  location: build_openai_client.py
  annotations: |
    Construct an OpenAI SDK client from `SWAX_LLM_*` environment variables.
    
    `client`: ready-to-use `OpenAI` instance for `OpenAIAdapter`.
    
    Algorithm:
    1. Call `require_vars` to fail fast on missing credentials.
    2. Read `SWAX_LLM_TOKEN` and `SWAX_LLM_BASE_URL` from `os.environ`.
    3. Construct `OpenAI(api_key=token, base_url=base_url)`.
    
    Requirements:
    - Never hardcode credentials.
    - Base URL must already be validated (no `/v1`) — SDK adds the version segment itself.
    
    Use `openai` for the client construction pattern.

"build_llm_client() -> client: LLMClient":
  location: build_llm_client.py
  annotations: |
    Factory selecting the adapter based on `SWAX_LLM_PROTOCOL`.
    
    `client`: an `LLMClient`-shaped adapter wrapping the chosen SDK client.
    
    Algorithm:
    1. Read `SWAX_LLM_PROTOCOL` from `os.environ`.
    2. If `"anthropic"`, return `AnthropicAdapter(build_anthropic_client())`.
    3. If `"openai"`, return `OpenAIAdapter(build_openai_client())`.
    4. Otherwise raise `UnsupportedLLMProtocolError`.
    
    Requirements:
    - Protocol value must be one of the supported identifiers — `parse_protocol` validation happens upstream in `config/`.
    - Switching providers must not require code changes in consumers.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Provider-agnostic LLM transport: protocol, Anthropic/OpenAI adapters, and factory by `SWAX_LLM_PROTOCOL`.
```

#### .usages file: `swax/llm/.usages/llm-transport.md`

```md
# LLM transport — провайдер-агностичный доступ к LLM API

## Предметная область

Шаблоны работы с LLM-клиентом: фабрика по `SWAX_LLM_PROTOCOL`, single-turn и multi-turn вызовы, обработка доменных ошибок. Целевая аудитория: cell `applications/discover/` (использует LLM для построения графа отслеживаемости).

Cell `llm/` инкапсулирует только транспорт — принимает готовые промпты и возвращает сырой текст ответа. Доменная логика (формирование промптов, парсинг JSON, multi-turn orchestration) лежит в потребителе. Провайдеры (Anthropic, OpenAI) переключаются переменной окружения без изменения кода потребителя.

---

## Получение клиента

`build_llm_client` выбирает адаптер на основе `SWAX_LLM_PROTOCOL`:

```python
from swax.llm import build_llm_client, LLMClient

def get_llm() -> LLMClient:
    return build_llm_client()
```

Соглашения потребителя:
- Перед вызовом убедиться, что `require_vars` (cell `config/`) уже отработал — иначе `MissingEnvironmentVariablesError` вылетит изнутри `build_*_client`.
- При неизвестном protocol выбрасывает `UnsupportedLLMProtocolError` — CLI-handler маппит в `click.ClickException`.
- Возвращает объект, удовлетворяющий протоколу `LLMClient` — конкретный тип адаптера скрыт.

---

## Single-turn вызов

`ask` отправляет один system + один user, возвращает сырой текст ответа:

```python
from swax.prompts import build_graph_system_prompt, build_graph_user_prompt
from swax.llm import build_llm_client

def first_pass(endpoints: list[str]) -> str:
    client = build_llm_client()
    system = build_graph_system_prompt()
    user = build_graph_user_prompt(endpoints)
    return client.ask(system=system, user=user)
```

Соглашения потребителя:
- Возвращает текст ответа (строка). Парсинг JSON — ответственность потребителя.
- При ошибке API выбрасывает `LLMCallError` или `LLMRateLimitedError`.

---

## Multi-turn вызов

`ask_multi_turn` отправляет system + упорядоченную историю сообщений — для уточняющего прохода:

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

Соглашения потребителя:
- `messages` — упорядоченный список ролей user/assistant. Порядок критичен — SDK строит контекст из него.
- system передаётся отдельно (не входит в `messages`) — у Anthropic и OpenAI разные конвенции, cell `llm/` инкапсулирует это.

---

## Обработка доменных исключений

Все ошибки API оборачиваются в доменные исключения. Политика повторов отсутствует — это ответственность потребителя:

```python
from swax.llm import LLMCallError, LLMRateLimitedError

def safe_llm_call(client, system, user):
    try:
        return client.ask(system=system, user=user)
    except LLMRateLimitedError:
        # опционально: retry с backoff
        raise
    except LLMCallError as exc:
        # click.ClickException(f"Сбой LLM: {exc.reason}")
        raise
```

`LLMRateLimitedError` и `LLMCallError` несут `reason` — оригинальное сообщение SDK.

---

## Тестирование

В тестах мокать SDK-клиент в точке импорта (conventions — Моки). Не вызывать live API:

```python
def test_first_pass(mocker):
    mock_client = mocker.MagicMock()
    mock_client.ask.return_value = '{"endpoints": []}'
    # ... передать mock_client напрямую в use-case ...
```

Адаптеры принимают SDK-клиент через инъекцию конструктора — это позволяет тестировать их с mock-объектами без патчинга.
```

---

### Cell 8/12: `swax/applications/init/` (created anew)

#### CODEMANIFEST: `swax/applications/init/CODEMANIFEST`

```yaml
Imports:
  - Types:
      - Config
      - GitConfig
      - SpecsConfig
      - save_config
    Usages:
      - project-config
    From: swax/config
  - Types:
      - clone_specs
      - RepositoryCloneError
      - SpecsNotFoundError
    Usages:
      - specs-repository
    From: swax/git
  - Types:
      - ensure_swax_dir
      - copy_specs
    Usages:
      - project-layout
    From: swax/fs

Usages:
  conventions: .goga/usages/conventions.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `project-config` from Imports for `Config` construction and `save_config` semantics.
  Use `specs-repository` from Imports for `clone_specs` context manager and propagated exceptions.
  Use `project-layout` from Imports for `ensure_swax_dir` and `copy_specs` semantics.
  
  Use relative imports inside the cell.
  This cell orchestrates only — no business logic, no SDK calls, no I/O beyond delegated routines.
  Domain exceptions from `git/` propagate up uncaught — the CLI handler maps them to `click.ClickException`.
  Log INFO at start/end of initialization with project metadata; never log credentials.

---

"run_init(repo_url: str, specs_location: str, download_path: pathlib.Path, project_root: pathlib.Path) -> None":
  location: run_init.py
  annotations: |
    Use-case "initialize project": persist configuration, clone the repository, copy specs into the local path.
    
    `repo_url`: clone URL of the source repository (collected by CLI prompts).
    `specs_location`: subdirectory inside the repo holding the specs.
    `download_path`: local destination for the copied specs (from `SpecsConfig.location` semantics).
    `project_root`: root of the Swax project — `.swax/` lives here.
    
    Algorithm:
    1. Build `Config(git=GitConfig(url=repo_url, location=specs_location), specs=SpecsConfig(type="openapi", location=str(download_path)))`.
    2. `swax_dir = ensure_swax_dir(project_root)`.
    3. `save_config(config, swax_dir / "config.yml")`.
    4. Enter `with clone_specs(repo_url, specs_location) as specs_path:`.
    5. Inside the context: `copy_specs(source=specs_path, destination=project_root / download_path)`.
    6. Log INFO completion.
    
    Requirements:
    - Configuration must be written before cloning — if clone fails, the user still has `.swax/config.yml` to inspect.
    - `clone_specs` context guarantees cleanup of the temporary directory on any outcome.
    
    Constraints:
    - Do not catch `RepositoryCloneError` / `SpecsNotFoundError` — let them propagate to the CLI handler.
    - Do not mutate `project_root` or `download_path` — treat as read-only inputs.
    
    Use `project-config` for the Config assembly.
    Use `specs-repository` for the clone lifecycle.
    Use `project-layout` for directory and copy operations.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Application-layer use-case for project initialization (config → clone → copy orchestration).
```

#### .usages file: `swax/applications/init/.usages/initialize-project.md`

```md
# Initialize project — use-case инициализации Swax

## Предметная область

Шаблон вызова use-case-а инициализации проекта Swax. Целевая аудитория: cell `commands/init/` (CLI-handler собирает входные данные из интерактивных промптов и делегирует в `run_init`).

Use-case оркеструет три доменных cell-а: `config/` (запись конфигурации), `git/` (клонирование репозитория), `fs/` (создание `.swax/` и копирование спецификаций). Это гексагональный application-слой — без бизнес-логики, только последовательность вызовов.

---

## Запуск use-case

`run_init` принимает все входы явно — для тестируемости и независимости от CLI:

```python
from pathlib import Path

from swax.applications.init import run_init

def initialize(repo_url: str, specs_location: str, download_path: Path, project_root: Path) -> None:
    run_init(
        repo_url=repo_url,
        specs_location=specs_location,
        download_path=download_path,
        project_root=project_root,
    )
```

Соглашения потребителя:
- `repo_url` — clone URL репозитория (из интерактивного промпта).
- `specs_location` — подкаталог в репозитории со спецификациями.
- `download_path` — локальный путь для сохранения спецификаций.
- `project_root` — корень проекта (обычно `pathlib.Path.cwd()`).

---

## Что выполняется внутри

Use-case выполняет шаги в строго определённом порядке:

1. Собирает `Config` с `GitConfig` и `SpecsConfig` из входов.
2. Создаёт `.swax/` через `ensure_swax_dir`.
3. Сохраняет `.swax/config.yml` через `save_config` — конфигурация пишется ДО клонирования, чтобы пользователь мог её проверить даже при сбое клонирования.
4. Клонирует репозиторий через `clone_specs` (context manager — cleanup гарантирован).
5. Копирует спецификации из временного клона в `download_path` через `copy_specs`.

---

## Обработка доменных исключений

`run_init` НЕ перехватывает исключения из `git/` (`RepositoryCloneError`, `SpecsNotFoundError`) — они распространяются наверх. CLI-handler в `commands/init/` маппит их в `click.ClickException`:

```python
from swax.applications.init import run_init
from swax.git import RepositoryCloneError, SpecsNotFoundError

def safe_initialize(repo_url, specs_location, download_path, project_root):
    try:
        run_init(repo_url, specs_location, download_path, project_root)
    except RepositoryCloneError as exc:
        # click.ClickException(f"Не удалось клонировать {exc.url}: {exc.reason}")
        ...
    except SpecsNotFoundError as exc:
        # click.ClickException(f"Спецификации не найдены в {exc.path}")
        ...
```

Это разделение ответственности: application layer не знает про CLI/Click, только оркеструет доменные cell-ы.

---

## Тестирование

`run_init` принимает все входы явно — тестируется без mock CLI. Использовать `tmp_path` для `project_root` и `download_path`:

```python
def test_run_init_persists_config(tmp_path):
    project_root = tmp_path
    download_path = tmp_path / "specs"
    # mock clone_specs и copy_specs в точке импорта для unit-теста
    # или интеграционный тест с реальным локальным git-репозиторием в tmp_path
    run_init("https://example.com/repo.git", "specs/", download_path, project_root)
    assert (project_root / ".swax" / "config.yml").exists()
```
```

---

### Cell 9/12: `swax/applications/discover/` (created anew)

#### CODEMANIFEST: `swax/applications/discover/CODEMANIFEST`

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
      - discover_specs
      - parse_spec
      - extract_paths
      - extract_schemas
    Usages:
      - parsing
      - extraction
    From: swax/openapi
  - Types:
      - LLMClient
      - build_llm_client
      - LLMCallError
      - LLMRateLimitedError
    Usages:
      - llm-transport
    From: swax/llm
  - Types:
      - build_graph_system_prompt
      - build_graph_user_prompt
      - build_refine_user_prompt
    Usages:
      - traceability-llm-prompts
    From: swax/prompts
  - Types:
      - TraceabilityGraph
      - save_traceability
    Usages:
      - graph-lifecycle
    From: swax/traceability

Usages:
  conventions: .goga/usages/conventions.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `project-config` from Imports for `load_config`.
  Use `environment` from Imports for `require_vars` (lazy LLM credential validation).
  Use `parsing` from Imports for `discover_specs` and `parse_spec`.
  Use `extraction` from Imports for `extract_paths` and `extract_schemas`.
  Use `llm-transport` from Imports for `build_llm_client` and `LLMClient` calls.
  Use `traceability-llm-prompts` from Imports for prompt assembly.
  Use `graph-lifecycle` from Imports for `TraceabilityGraph` and `save_traceability`.
  
  Use relative imports inside the cell.
  Domain exceptions from `llm/` propagate uncaught — the CLI handler maps them.
  The graph stores paths only — no HTTP methods.
  Edge deduplication is mandatory before saving.
  Logging: INFO at start/end, DEBUG for intermediate steps; never log `SWAX_LLM_TOKEN`.
  
  Defensive JSON parsing of LLM responses (inline — provider-agnostic):
  - Strip any prose/fences around the JSON payload before `json.loads`.
  - Wrap `json.JSONDecodeError` into a meaningful domain error carrying the raw payload excerpt for diagnostics.
  - Validate the parsed shape is `dict[str, list[str]]`; coerce or reject on mismatch.
  - Never trust LLM output structure — schema-validate before consuming.

---

"run_discover(project_root: pathlib.Path) -> None":
  location: run_discover.py
  annotations: |
    Use-case "build traceability graph": full rebuild from scratch, ignoring any existing graph.
    
    `project_root`: root of the Swax project — `.swax/config.yml` describes specs, `.swax/traceability.yml` is overwritten.
    
    Algorithm:
    1. Call `require_vars` to fail fast on missing LLM credentials.
    2. `config = load_config(project_root / ".swax" / "config.yml")`.
    3. Resolve specs root as `project_root / config.specs.location`.
    4. `spec_files = discover_specs(specs_root)`.
    5. For each `spec_path`: `spec = parse_spec(spec_path)`; `extend endpoints with extract_paths(spec)` and `merge schemas with extract_schemas(spec)`.
    6. `client = build_llm_client()`.
    7. `system = build_graph_system_prompt()` and `first_user = build_graph_user_prompt(endpoints)`.
    8. `raw_first = client.ask(system, first_user)`; defensively parse JSON (strip prose, wrap `json.JSONDecodeError`, validate `dict[str, list[str]]` shape) into `first_dependencies`.
    9. Extract `ambiguous_pairs` from `first_dependencies` (pairs flagged uncertain by the LLM).
    10. `refine_user = build_refine_user_prompt(ambiguous_pairs, schemas)`.
    11. `raw_refined = client.ask_multi_turn(system, messages=[{user, first_user}, {assistant, raw_first}, {user, refine_user}])`; defensively parse JSON into `final_dependencies`.
    12. `graph = TraceabilityGraph(edges={})`; for each source, targets pair call `graph.add_edge` for each target.
    13. `graph.deduplicate()`.
    14. `save_traceability(graph, project_root / ".swax" / "traceability.yml")`.
    15. Log INFO completion.
    
    Requirements:
    - Always build a fresh graph — do not read existing `.swax/traceability.yml`.
    - Spec order from `discover_specs` is deterministic (sorted) — endpoint order is stable across runs.
    - JSON parsing of LLM responses must be defensive — wrap `json.JSONDecodeError` into a meaningful error.
    
    Constraints:
    - Do not catch `LLMCallError` / `LLMRateLimitedError` — let them propagate to the CLI handler.
    - Do not store schemas in the graph — paths only.
    - Do not embed filesystem paths or credentials into prompts — cell `prompts/` already enforces this.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Application-layer use-case for full traceability graph rebuild (two-pass LLM analysis scenario).
```

#### .usages file: `swax/applications/discover/.usages/discover-traceability.md`

```md
# Discover traceability — use-case полного перестроения графа

## Предметная область

Шаблон вызова use-case-а полного перестроения графа отслеживаемости API. Целевая аудитория: cell `commands/discover/` (CLI-handler делегирует в `run_discover` после загрузки `.env`).

Use-case оркеструет пять доменных cell-ов в двухпроходном LLM-сценарии: `config/` (чтение конфигурации), `openapi/` (парсинг спецификаций), `prompts/` (сборка промптов), `llm/` (вызовы API), `traceability/` (сохранение графа). Локально cell выполняет защитный JSON-парсинг и формирование multi-turn сообщений.

---

## Запуск use-case

`run_discover` принимает только `project_root` — остальные входы читаются из `.swax/config.yml`:

```python
from pathlib import Path

from swax.applications.discover import run_discover

def rebuild_graph(project_root: Path) -> None:
    run_discover(project_root=project_root)
```

Соглашения потребителя:
- Команда требует LLM creds — `require_vars` выполняется внутри use-case, и `MissingEnvironmentVariablesError` распространяется наверх для CLI-handler.
- Проект должен быть инициализирован (`init`) — `.swax/config.yml` обязан существовать.
- Всегда создаёт свежий граф, игнорируя существующий `.swax/traceability.yml`.

---

## Что выполняется внутри (двухпроходный сценарий)

Use-case выполняет 15 шагов:

**Подготовка (шаги 1-5):**
1. `require_vars` — fail fast при отсутствии LLM creds.
2. `load_config` — чтение `.swax/config.yml`.
3. Определение корня спецификаций из `config.specs.location`.
4. `discover_specs` — список файлов спецификаций.
5. Для каждой спецификации: `parse_spec` → `extract_paths` (накопление endpoints) + `extract_schemas` (накопление schema context).

**Первый LLM-проход (шаги 6-9):**
6. `build_llm_client` — фабрика по `SWAX_LLM_PROTOCOL`.
7. `build_graph_system_prompt` + `build_graph_user_prompt(endpoints)`.
8. `client.ask(system, first_user)` → защитный JSON-парсинг → гипотезы зависимостей.
9. Извлечение неоднозначных пар (пары, помеченные LLM как неуверенные).

**Уточняющий LLM-проход (шаги 10-11):**
10. `build_refine_user_prompt(ambiguous_pairs, schemas)`.
11. `client.ask_multi_turn(system, [initial_user, assistant_response, refine_user])` → защитный JSON-парсинг → финальные зависимости.

**Сборка и сохранение графа (шаги 12-15):**
12. `TraceabilityGraph(edges={})` + `add_edge` для каждой пары зависимостей.
13. `graph.deduplicate()` — удаление дублей и self-loops.
14. `save_traceability(graph, .swax/traceability.yml)`.
15. INFO-лог завершения.

---

## Обработка доменных исключений

`run_discover` НЕ перехватывает исключения — они распространяются наверх. CLI-handler маппит:

```python
from swax.applications.discover import run_discover
from swax.config import MissingEnvironmentVariablesError
from swax.llm import LLMCallError, LLMRateLimitedError
from swax.openapi import SpecParseError

def safe_discover(project_root):
    try:
        run_discover(project_root=project_root)
    except MissingEnvironmentVariablesError as exc:
        # click.ClickException(f"Отсутствуют переменные: {', '.join(exc.missing)}")
        ...
    except SpecParseError as exc:
        # click.ClickException(f"Ошибка разбора {exc.path}: {exc.reason}")
        ...
    except LLMRateLimitedError:
        # click.ClickException("Превышен rate limit LLM")
        ...
    except LLMCallError as exc:
        # click.ClickException(f"Сбой LLM: {exc.reason}")
        ...
```

Application layer не знает про CLI/Click — это разделение ответственности.

---

## Тестирование

`run_discover` тестируется через mock в точке импорта доменных routines. Использовать `tmp_path` для `project_root` и предзаписанный `.swax/config.yml`:

```python
def test_run_discover_builds_graph(tmp_path, mocker):
    # подготовка .swax/config.yml в tmp_path
    # mock discover_specs, parse_spec, extract_paths возвращают фикстуры
    # mock build_llm_client и LLMClient.ask/ask_multi_turn возвращают JSON-ответы
    run_discover(project_root=tmp_path)
    assert (tmp_path / ".swax" / "traceability.yml").exists()
```

Не вызывать live LLM API в тестах — всегда mock.
```

---

### Cell 10/12: `swax/commands/init/` (created anew)

#### CODEMANIFEST: `swax/commands/init/CODEMANIFEST`

```yaml
Imports:
  - Types:
      - SwaxContext
    Usages:
      - cli-facade
    From: swax/cli
  - Types:
      - run_init
    Usages:
      - initialize-project
    From: swax/applications/init
  - Types:
      - RepositoryCloneError
      - SpecsNotFoundError
    Usages:
      - specs-repository
    From: swax/git

Usages:
  conventions: .goga/usages/conventions.md
  click: .goga/usages/cooks/click.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `click` for command decorator, prompts, and error mapping.
  Use `initialize-project` from Imports for `run_init` semantics.
  Use `specs-repository` from Imports for propagated exception types.
  Use `cli-facade` from Imports for `SwaxContext` access pattern.
  
  Use relative imports inside the cell.
  The handler stays thin — only CLI parsing and exception mapping; orchestration lives in `run_init`.
  Map domain exceptions to `click.ClickException` for uniform exit codes.

---

"init(ctx: click.Context) -> None":
  location: init.py
  annotations: |
    Click handler for the `init` command: prompt the user, delegate to `run_init`, map domain exceptions.
    
    `ctx`: Click context whose `obj` is a `SwaxContext` carrying the env file path.
    
    Algorithm:
    1. Resolve `ctx.obj` as `SwaxContext` via `@click.pass_obj`.
    2. Prompt `repo_url` via `click.prompt`.
    3. Prompt `specs_location` via `click.prompt`.
    4. Prompt `download_path` via `click.prompt`, coercing to `pathlib.Path`.
    5. Resolve `project_root = pathlib.Path.cwd()`.
    6. Call `run_init(repo_url, specs_location, download_path, project_root)` inside a `try`.
    7. On `RepositoryCloneError`, raise `click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")`.
    8. On `SpecsNotFoundError`, raise `click.ClickException(f"Specs not found at {exc.path}")`.
    
    Requirements:
    - Prompts must be the sole source of user input — no command-line options for these values in task 1.
    - Exit code 0 on success, 1 on any `ClickException` (Click default).
    
    Constraints:
    - Do not catch generic `Exception` — only the two domain exceptions from `git/`.
    - Do not log credentials — prompts collect only repo URL and paths.
    
    Use `click` for the command pattern and prompt helpers.
    Use `initialize-project` for the delegated use-case contract.
    Use `specs-repository` for the exception semantics.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Click handler for the `init` command — interactive prompts and exception mapping to ClickException.
```

#### .usages file: `swax/commands/init/.usages/init-command.md`

```md
# Init command — Click-handler команды `init`

## Предметная область

Шаблон регистрации и вызова Click-команды `init`. Целевая аудитория: cell `swax/cli/` (регистрирует команду на главной группе `main` через `main.add_command(init)`).

Команда тонкая — только интерактивные промпты и маппинг ошибок. Прикладная логика (клонирование, копирование, запись конфигурации) делегируется в `run_init` (cell `applications/init/`).

---

## Регистрация команды

`init` — это декорированный `@click.command` callback. Регистрация на главной группе:

```python
from swax.cli import main
from swax.commands.init import init

main.add_command(init)
```

Соглашения потребителя:
- Команда не принимает CLI-опций — все входы собираются через интерактивные промпты.
- Контекст передаётся через `@click.pass_obj` — `SwaxContext` из cell `cli/`.

---

## Выполнение команды

При вызове `swax init` команда:

1. Получает `SwaxContext` через `@click.pass_obj`.
2. Промптит `repo_url`, `specs_location`, `download_path` через `click.prompt`.
3. Определяет `project_root = pathlib.Path.cwd()`.
4. Делегирует в `run_init(repo_url, specs_location, download_path, project_root)`.
5. Перехватывает `RepositoryCloneError` / `SpecsNotFoundError` и маппит в `click.ClickException`.

---

## Обработка ошибок

Доменные исключения из `git/` маппятся в `click.ClickException` для единообразных exit codes:

- `RepositoryCloneError` → `click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")`
- `SpecsNotFoundError` → `click.ClickException(f"Specs not found at {exc.path}")`

Exit codes: `0` — успех, `1` — сбой (Click default для `ClickException`).

---

## Тестирование

Тестировать через `click.testing.CliRunner`, вызывая callback напрямую без subprocess:

```python
from click.testing import CliRunner
from swax.commands.init import init

def test_init_prompts_and_delegates(mocker):
    mocker.patch("swax.commands.init.run_init")
    runner = CliRunner()
    result = runner.invoke(init, input="https://example.com/repo.git\nspecs/\n./local_specs\n")
    assert result.exit_code == 0
```

В тестах мокать `run_init` в точке импорта — не выполнять реальное клонирование.
```

---

### Cell 11/12: `swax/commands/discover/` (created anew)

#### CODEMANIFEST: `swax/commands/discover/CODEMANIFEST`

```yaml
Imports:
  - Types:
      - SwaxContext
    Usages:
      - cli-facade
    From: swax/cli
  - Types:
      - run_discover
    Usages:
      - discover-traceability
    From: swax/applications/discover
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
      - LLMCallError
      - LLMRateLimitedError
      - UnsupportedLLMProtocolError
    Usages:
      - llm-transport
    From: swax/llm

Usages:
  conventions: .goga/usages/conventions.md
  click: .goga/usages/cooks/click.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `click` for command decorator and error mapping.
  Use `discover-traceability` from Imports for `run_discover` semantics.
  Use `environment` from Imports for `MissingEnvironmentVariablesError` semantics.
  Use `parsing` from Imports for `SpecParseError` semantics.
  Use `llm-transport` from Imports for LLM exception semantics.
  Use `cli-facade` from Imports for `SwaxContext` access pattern.
  
  Use relative imports inside the cell.
  The handler stays thin — only exception mapping; orchestration lives in `run_discover`.
  Map every domain exception to `click.ClickException` with a user-facing message.

---

"discover(ctx: click.Context) -> None":
  location: discover.py
  annotations: |
    Click handler for the `discover` command: delegate to `run_discover`, map domain exceptions to user-facing errors.
    
    `ctx`: Click context whose `obj` is a `SwaxContext`.
    
    Algorithm:
    1. Resolve `ctx.obj` as `SwaxContext` via `@click.pass_obj`.
    2. Resolve `project_root = pathlib.Path.cwd()`.
    3. Call `run_discover(project_root)` inside a `try`.
    4. On `MissingEnvironmentVariablesError`, raise `click.ClickException(f"Missing env vars: {', '.join(exc.missing)}")`.
    5. On `SpecParseError`, raise `click.ClickException(f"Failed to parse {exc.path}: {exc.reason}")`.
    6. On `LLMRateLimitedError`, raise `click.ClickException("LLM rate limited; retry later")`.
    7. On `LLMCallError`, raise `click.ClickException(f"LLM call failed: {exc.reason}")`.
    8. On `UnsupportedLLMProtocolError`, raise `click.ClickException(f"Unsupported LLM protocol: {exc.protocol}")`.
    
    Requirements:
    - No interactive prompts — `discover` reads everything from `.swax/config.yml` and the environment.
    - Exit code 0 on success, 1 on any `ClickException`.
    
    Constraints:
    - Do not catch generic `Exception` — only the documented domain exceptions.
    - Do not retry rate-limited calls — surface them to the user.
    - Do not log `SWAX_LLM_TOKEN` in any error message.
    
    Use `click` for the command pattern.
    Use `discover-traceability` for the delegated use-case contract.
    Use `environment`, `parsing`, `llm-transport` from Imports for exception semantics.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  Click handler for the `discover` command — exception mapping from domain errors to ClickException.
```

#### .usages file: `swax/commands/discover/.usages/discover-command.md`

```md
# Discover command — Click-handler команды `discover`

## Предметная область

Шаблон регистрации и вызова Click-команды `discover`. Целевая аудитория: cell `swax/cli/` (регистрирует команду на главной группе `main` через `main.add_command(discover)`).

Команда тонкая — только маппинг ошибок. Прикладная логика (парсинг спецификаций, LLM-анализ, сборка графа) делегируется в `run_discover` (cell `applications/discover/`). В отличие от `init`, `discover` не имеет интерактивных промптов — все входы из `.swax/config.yml` и окружения.

---

## Регистрация команды

`discover` — это декорированный `@click.command` callback. Регистрация на главной группе:

```python
from swax.cli import main
from swax.commands.discover import discover

main.add_command(discover)
```

Соглашения потребителя:
- Команда не принимает CLI-опций и не имеет промптов.
- Контекст передаётся через `@click.pass_obj` — `SwaxContext` из cell `cli/`.
- Требует предварительно загруженный `.env` (callback группы `main` уже вызвал `load_env`).

---

## Выполнение команды

При вызове `swax discover` команда:

1. Получает `SwaxContext` через `@click.pass_obj`.
2. Определяет `project_root = pathlib.Path.cwd()`.
3. Делегирует в `run_discover(project_root)`.
4. Перехватывает доменные исключения из `config/`, `openapi/`, `llm/` и маппит в `click.ClickException`.

---

## Обработка ошибок

Все доменные исключения маппятся в `click.ClickException` с понятными сообщениями:

| Exception | Сообщение |
|-----------|-----------|
| `MissingEnvironmentVariablesError` | `Missing env vars: {missing}` |
| `SpecParseError` | `Failed to parse {path}: {reason}` |
| `LLMRateLimitedError` | `LLM rate limited; retry later` |
| `LLMCallError` | `LLM call failed: {reason}` |
| `UnsupportedLLMProtocolError` | `Unsupported LLM protocol: {protocol}` |

Exit codes: `0` — успех, `1` — сбой (Click default для `ClickException`).

Команда НЕ повторяет rate-limited вызовы и НЕ логирует `SWAX_LLM_TOKEN` в сообщениях об ошибках.

---

## Тестирование

Тестировать через `click.testing.CliRunner`, мокая `run_discover` в точке импорта:

```python
from pathlib import Path

from click.testing import CliRunner

def test_discovers_graph_on_success(mocker, tmp_path):
    mocker.patch("swax.commands.discover.run_discover")
    runner = CliRunner()
    result = runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
    assert result.exit_code == 0

def test_discovers_maps_missing_env_vars(mocker):
    def raise_missing(project_root):
        raise MissingEnvironmentVariablesError(missing=["SWAX_LLM_TOKEN"])
    mocker.patch("swax.commands.discover.run_discover", side_effect=raise_missing)
    runner = CliRunner()
    result = runner.invoke(discover, obj=SwaxContext(env_file=Path(".env")))
    assert result.exit_code == 1
    assert "SWAX_LLM_TOKEN" in result.output
```

Не вызывать live LLM API в тестах — всегда mock `run_discover`.
```

---

### Cell 12/12: `swax/cli/` (created anew)

#### CODEMANIFEST: `swax/cli/CODEMANIFEST`

```yaml
Imports:
  - Types:
      - load_env
    Usages:
      - environment
    From: swax/config

Usages:
  conventions: .goga/usages/conventions.md
  click: .goga/usages/cooks/click.md

Annotations: |
  Use `conventions` for code writing rules and testing.
  Use `click` for entry point group, `--env-file` option, and pass object pattern.
  Use `environment` from Imports for `load_env` semantics.
  
  Use relative imports inside the cell.
  Register subcommands through lazy import in `__main__.py` — never import `commands/*` in `__init__.py` to avoid circular cell dependencies.
  Load environment before any subcommand executes.
  Export `main` and `SwaxContext` via `__all__` as the facade.

---

"main(ctx: click.Context, env_file: pathlib.Path) -> None":
  location: main.py
  annotations: |
    CLI entry point: top-level Click group with `--env-file` option that loads the environment and initializes `SwaxContext` for subcommands.
    
    `ctx`: Click context object holding the `SwaxContext`.
    `env_file`: path to the environment file (default `.env`).
    
    Algorithm:
    1. Decorate with `@click.group` and an `--env-file` option with `type=click.Path(exists=False, dir_okay=False, path_type=pathlib.Path), default=".env", show_default=True`.
    2. Decorate the callback with `@click.pass_context`.
    3. Call `load_env(env_file)`.
    4. Set `ctx.obj = SwaxContext(env_file=env_file)`.
    
    Requirements:
    - Must be registered as `swax = "swax.cli.__main__:main"` in `[project.scripts]`.
    - Subcommands `init` and `discover` are registered in `__main__.py` via lazy import, NOT in this callback.
    
    Constraints:
    - Do not raise on missing `.env` — `load_env` handles it.
    - Do not read `SWAX_*` variables here — validation happens lazily inside subcommands.
    
    Use `click` for the entry point pattern.
    Use `environment` for the `load_env` contract.

"SwaxContext(env_file: pathlib.Path)":
  location: SwaxContext.py
  annotations: |
    Click pass object carrying CLI parameters between `main` and its subcommands.
    
    `env_file`: path to the environment file, passed via `--env-file`.
    
    Requirements:
    - Constructed in the `main` group callback and stored as `ctx.obj`.
    - Subcommands receive it via `@click.pass_obj`.
    - `config` remains `None` — subcommands load configuration on demand via `load_config`.
    
    Use `conventions` for pydantic model rules (`kw_only=True`).
  properties:
    "env_file -> pathlib.Path": |
      Path to the environment file. Read-only after construction — passed as input to `load_env`.
    "config -> Config | None": |
      Cached project configuration, defaults to `None`. Subcommands may lazily populate it via `load_config`; optional because `init` writes config rather than reading it.

---

Author: Goga
CreatedAt: 25/06/26
Description: |
  CLI entry point (Click group with `--env-file`) and `SwaxContext` pass object.
```

#### .usages file: `swax/cli/.usages/cli-facade.md`

```md
# CLI facade — точка входа и pass object

## Предметная область

Шаблоны использования точки входа CLI Swax и pass object `SwaxContext`. Целевая аудитория: cell-ы `commands/init/` и `commands/discover/` (регистрируются на группе `main` и читают `SwaxContext` через `@click.pass_obj`).

Click — единственный CLI-фреймворк Swax. Группа `main` верхнего уровня с опцией `--env-file` загружает окружение перед выполнением любой подкоманды.

---

## Регистрация подкоманд

Подкоманды `init` и `discover` регистрируются на группе `main` через `main.add_command()`. Чтобы избежать циклических импортов между `cli/` и `commands/`, регистрация выполняется лениво в `__main__.py` ячейки `cli/`:

```python
# swax/cli/__main__.py
from swax.cli import main

# Ленивая регистрация — разрывает цикл cli/ <-> commands/
from swax.commands.init import init
from swax.commands.discover import discover

main.add_command(init)
main.add_command(discover)

if __name__ == "__main__":
    main()
```

Соглашения потребителя:
- `main` — это группа Click верхнего уровня, декорированная `@click.group`.
- Скрипт точки входа `swax` указывает на `swax.cli.__main__:main` в `[project.scripts]`.
- Команды импортируются только в `__main__.py`, не в `__init__.py` — это сохраняет контракт CODEMANIFEST без цикла.

---

## Использование SwaxContext в подкоманде

Подкоманды получают `SwaxContext` через `@click.pass_obj`. Контекст несёт `env_file`; конфигурация проекта подгружается лениво:

```python
import click

from swax.cli import SwaxContext

@click.command()
@click.pass_obj
def my_command(ctx: SwaxContext) -> None:
    # ctx.env_file — путь к .env, уже загруженному callback-ом main
    # ctx.config — None по умолчанию; подгрузите через load_config при необходимости
    pass
```

Соглашения потребителя:
- `env_file` — только для чтения после конструирования; уже передан в `load_env` callback-ом группы.
- `config` — опциональный кэш конфигурации. Команда `init` не использует его (она записывает конфигурацию). Команда `discover` подгружает конфигурацию через `load_config` внутри use-case, а не через контекст.

---

## Опция --env-file

Конечный пользователь передаёт `.env` через `--env-file`:

```bash
swax --env-file .env discover
swax --env-file /path/to/.env init
```

По умолчанию `--env-file .env`. Переменные окружения, уже заданные в shell, имеют приоритет над файлом (`override=False` в `load_dotenv`).

---

## Тестирование

Тестировать точку входа через `CliRunner`, передавая mock `SwaxContext` через `obj=`:

```python
from pathlib import Path

from click.testing import CliRunner

def test_main_loads_env(mocker, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SWAX_LLM_TOKEN=test\n")
    
    mock_load_env = mocker.patch("swax.cli.load_env")
    runner = CliRunner()
    result = runner.invoke(main, ["--env-file", str(env_file), "init"], input="\n\n\n")
    assert mock_load_env.called
```

В тестах `load_env` можно мокать, чтобы избежать реальной записи в `os.environ`.
```

---

## Dependency Map

```
[Уровень 0: листья — без Imports.Types]
  swax/config/        swax/fs/          swax/git/         swax/openapi/
  swax/traceability/  swax/prompts/

[Уровень 1: cell-ы, зависящие от листьев]
  swax/llm/                       → swax/config/ (require_vars, MissingEnvironmentVariablesError)
  swax/applications/init/         → swax/config/, swax/git/, swax/fs/
  swax/applications/discover/     → swax/config/, swax/openapi/, swax/llm/, swax/prompts/, swax/traceability/

[Уровень 2: command handlers]
  swax/commands/init/             → swax/cli/, swax/applications/init/, swax/git/
  swax/commands/discover/         → swax/cli/, swax/applications/discover/, swax/config/, swax/openapi/, swax/llm/

[Уровень 3: entry point]
  swax/cli/                       → swax/config/ (load_env)
              (команды регистрируются лениво в __main__.py — без Imports из commands/*)
```

**Таблица связей через Imports:**

| Source cell | Imported types | Target cell |
|-------------|----------------|-------------|
| `swax/llm/` | `require_vars`, `MissingEnvironmentVariablesError` | `swax/config/` |
| `swax/applications/init/` | `Config`, `GitConfig`, `SpecsConfig`, `save_config` | `swax/config/` |
| `swax/applications/init/` | `clone_specs`, `RepositoryCloneError`, `SpecsNotFoundError` | `swax/git/` |
| `swax/applications/init/` | `ensure_swax_dir`, `copy_specs` | `swax/fs/` |
| `swax/applications/discover/` | `load_config`, `require_vars`, `Config` | `swax/config/` |
| `swax/applications/discover/` | `discover_specs`, `parse_spec`, `extract_paths`, `extract_schemas` | `swax/openapi/` |
| `swax/applications/discover/` | `LLMClient`, `build_llm_client`, `LLMCallError`, `LLMRateLimitedError` | `swax/llm/` |
| `swax/applications/discover/` | `build_graph_system_prompt`, `build_graph_user_prompt`, `build_refine_user_prompt` | `swax/prompts/` |
| `swax/applications/discover/` | `TraceabilityGraph`, `save_traceability` | `swax/traceability/` |
| `swax/commands/init/` | `SwaxContext` | `swax/cli/` |
| `swax/commands/init/` | `run_init` | `swax/applications/init/` |
| `swax/commands/init/` | `RepositoryCloneError`, `SpecsNotFoundError` | `swax/git/` |
| `swax/commands/discover/` | `SwaxContext` | `swax/cli/` |
| `swax/commands/discover/` | `run_discover` | `swax/applications/discover/` |
| `swax/commands/discover/` | `MissingEnvironmentVariablesError` | `swax/config/` |
| `swax/commands/discover/` | `SpecParseError` | `swax/openapi/` |
| `swax/commands/discover/` | `LLMCallError`, `LLMRateLimitedError`, `UnsupportedLLMProtocolError` | `swax/llm/` |
| `swax/cli/` | `load_env` | `swax/config/` |

**Ацикличность подтверждена:** направленный граф от листьев (уровень 0) к корню (уровень 3), без циклов.

---

## Verification Checklist

После реализации каждого артефакта проверить:

### Общее (для всех 12 cell-ов)

- [ ] `goga lint` проходит без ошибок для каждого CODEMANIFEST
- [ ] `goga schema` показывает все 12 cell-ов с правильными зависимостями
- [ ] Все `location` значения соответствуют Python-соглашениям (`snake_case.py` для routines, `PascalCase.py` для entities)
- [ ] Все pydantic-модели используют `kw_only=True` (conventions)
- [ ] Все относительные импорты внутри cell-ов (conventions)
- [ ] Все публичные функции/классы имеют Google-style docstrings (conventions)

### Cell-специфичные проверки

| Cell | Что проверить после реализации |
|------|------------------------------|
| `swax/config/` | `load_config`/`save_config` корректно сериализуют `Config` через pydantic + pyyaml; `parse_protocol` отклоняет некорректные значения; `parse_base_url` отклоняет `/v1`/`/v2` |
| `swax/fs/` | `ensure_swax_dir` idempotent; `copy_specs` перезаписывает существующие файлы при повторном запуске |
| `swax/git/` | `clone_specs` — context manager, cleanup при исключении; `depth=1` shallow clone; `GitCommandError` → `RepositoryCloneError` |
| `swax/openapi/` | `parse_spec` через Prance с `$ref`-resolverом; `extract_paths` возвращает только пути без методов; `extract_schemas` различает OpenAPI 3.x и Swagger 2.0 |
| `swax/traceability/` | `TraceabilityGraph.deduplicate` убирает дубликаты и self-loops; `save_traceability` сортирует ключи и значения детерминированно |
| `swax/prompts/` | Все 3 промпт-билдера возвращают строки, запрашивающие JSON; без встраивания путей ФС/токенов |
| `swax/llm/` | `AnthropicAdapter`/`OpenAIAdapter` имеют идентичные сигнатуры `LLMClient`; `build_llm_client` выбирает адаптер по `SWAX_LLM_PROTOCOL`; `SWAX_LLM_TOKEN` не логируется |
| `swax/applications/init/` | `run_init` пишет конфиг ДО клонирования; использует `with clone_specs(...)`; исключения из `git/` распространяются без перехвата |
| `swax/applications/discover/` | `run_discover` выполняет 15 шагов в указанном порядке; JSON-парсинг защитный; `graph.deduplicate()` вызывается перед `save_traceability` |
| `swax/commands/init/` | `init` имеет 3 промпта; маппит `RepositoryCloneError`/`SpecsNotFoundError` в `ClickException`; exit codes 0/1 |
| `swax/commands/discover/` | `discover` не имеет промптов; маппит 5 типов доменных исключений; exit codes 0/1 |
| `swax/cli/` | `main` — Click-группа с `--env-file`; `SwaxContext` pydantic с `kw_only=True`; команды регистрируются лениво в `__main__.py` |

### Интеграционные проверки (после всех 12 cell-ов)

- [ ] `swax --help` показывает справку с командами `init` и `discover`
- [ ] `swax init` интерактивно опрашивает и создаёт `.swax/config.yml` + копирует спецификации
- [ ] `swax --env-file .env discover` парсит спецификации, строит граф, сохраняет в `.swax/traceability.yml`
- [ ] Переключение `SWAX_LLM_PROTOCOL=anthropic`/`openai` не требует изменения кода
- [ ] При отсутствии `SWAX_LLM_TOKEN`/некорректном protocol/base URL с `/v1` — осмысленные доменные ошибки
- [ ] Граф содержит только пути без дубликатов рёбер
- [ ] `pytest tests/ -x` проходит
- [ ] `ruff check swax/` без ошибок

### Acceptance Criteria (финальная проверка)

Все 11 критериев из [PRIMARY_ANALYSIS_REPORT] покрыты спроектированной архитектурой — см. Acceptance Criteria Check в [CELL_ASSEMBLY_REPORT].

---