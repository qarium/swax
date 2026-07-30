# Initialize project — use-case инициализации Swax

## Предметная область

Шаблон вызова use-case-а инициализации проекта Swax. Целевая аудитория: cell `commands/init/` (CLI-handler собирает входные данные из интерактивных промптов и делегирует в `run_init`).

Use-case оркеструет три доменных cell-а: `config/` (запись конфигурации), `git/` (клонирование репозитория), `fs/` (создание .swax/ и копирование спецификаций). Это гексагональный application-слой — без бизнес-логики, только последовательность вызовов.

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
- `project_root` — корень проекта (обычно pathlib.Path.cwd()).

---

## Что выполняется внутри

Use-case выполняет шаги в строго определённом порядке:

1. Собирает Config с GitConfig и SpecsConfig из входов.
2. Создаёт .swax/ через ensure_swax_dir.
3. Сохраняет .swax/config.yml через save_config — конфигурация пишется ДО клонирования, чтобы пользователь мог её проверить даже при сбое клонирования.
4. Клонирует репозиторий через clone_specs (context manager — cleanup гарантирован).
5. Копирует спецификации из временного клона в `download_path` через copy_specs.

---

## Обработка доменных исключений

`run_init` НЕ перехватывает исключения из `git/` (RepositoryCloneError, SpecsNotFoundError) — они распространяются наверх. CLI-handler в `commands/init/` маппит их в click.ClickException:

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

`run_init` принимает все входы явно — тестируется без mock CLI. Использовать tmp_path для `project_root` и `download_path`:

```python
def test_run_init_persists_config(tmp_path):
    project_root = tmp_path
    download_path = tmp_path / "specs"
    # mock clone_specs и copy_specs в точке импорта для unit-теста
    # или интеграционный тест с реальным локальным git-репозиторием в tmp_path
    run_init("https://example.com/repo.git", "specs/", download_path, project_root)
    assert (project_root / ".swax" / "config.yml").exists()
```
