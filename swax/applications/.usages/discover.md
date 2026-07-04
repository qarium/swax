# Discover traceability — use-case полного перестроения графа

## Предметная область

Шаблон вызова use-case-а полного перестроения графа отслеживаемости API. Целевая аудитория: cell `commands/discover/` (CLI-handler делегирует в `run_discover` после загрузки .env).

Use-case оркеструет пять доменных cell-ов в двухпроходном ЛЛМ-сценарии: `config/` (чтение конфигурации), `openapi/` (парсинг спецификаций), `prompts/` (сборка промптов), `llm/` (вызовы API), `traceability/` (сохранение графа). Локально cell выполняет защитный JSON-парсинг и формирование multi-turn сообщений.

---

## Запуск use-case

`run_discover` принимает только `project_root` — остальные входы читаются из .swax/config.yml:

```python
from pathlib import Path

from swax.applications.discover import run_discover

def rebuild_graph(project_root: Path) -> None:
    run_discover(project_root=project_root)
```

Соглашения потребителя:
- Команда требует LLM creds — require_vars выполняется внутри use-case, и MissingEnvironmentVariablesError распространяется наверх для CLI-handler.
- Проект должен быть инициализирован (init) — .swax/config.yml обязан существовать.
- Всегда создаёт свежий граф, игнорируя существующий .swax/traceability.yml.

---

## Что выполняется внутри (двухпроходный сценарий)

Use-case выполняет 15 шагов:

**Подготовка (шаги 1-5):**
1. require_vars — fail fast при отсутствии LLM creds.
2. load_config — чтение .swax/config.yml.
3. Определение корня спецификаций из config.specs.location.
4. discover_specs — список файлов спецификаций.
5. Для каждой спецификации: parse_spec -> extract_paths (накопление endpoints) + extract_schemas (накопление schema context).

**Первый ЛЛМ-проход (шаги 6-9):**
6. build_llm_client — фабрика по SWAX_LLM_PROTOCOL.
7. build_graph_system_prompt + build_graph_user_prompt(endpoints).
8. client.ask(system, first_user) -> защитный JSON-парсинг -> гипотезы зависимостей.
9. Извлечение неоднозначных пар (пары, помеченные LLM как неуверенные).

**Уточняющий ЛЛМ-проход (шаги 10-11):**
10. build_refine_user_prompt(ambiguous_pairs, schemas).
11. client.ask_multi_turn(system, [initial_user, assistant_response, refine_user]) -> защитный JSON-парсинг -> финальные зависимости.

**Сборка и сохранение графа (шаги 12-16):**
12. Merge confident edges из первого прохода с resolved uncertain pairs из refine-прохода. Refine переопределяет первый проход только при непустом adjacency-списке; пустой refine-ответ трактуется как «нет новой информации», и confident edges сохраняются.
13. Гарантируется, что каждый endpoint, извлечённый из спецификаций, присутствует в финальной map (с пустым списком, если рёбер нет).
14. Источники и цели вне множества endpoints отфильтровываются — это honourит контракт промпта, запрещающий пути вне endpoint universe.
15. TraceabilityGraph(edges={}) + add_edge для каждой пары зависимостей; endpoints без рёбер добавляются как ключи с пустым списком.
16. graph.deduplicate() — удаление дублей и self-loops (пустые ключи сохраняются как узлы графа), save_traceability(graph, .swax/traceability.yml), INFO-лог завершения.

---

## Обработка доменных исключений

`run_discover` НЕ перехватывает исключения — они распространяются наверх. CLI-handler маппит:

```python
from swax.applications.discover import run_discover
from swax.config import MissingEnvironmentVariablesError
from swax.llm import LLMCallError, LLMRateLimitedError, LLMResponseParseError
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
    except LLMResponseParseError as exc:
        # click.ClickException(f"Ошибка разбора ответа LLM: {exc.reason}")
        ...
```

Application layer не знает про CLI/Click — это разделение ответственности.

---

## Тестирование

`run_discover` тестируется через mock в точке импорта доменных routines. Использовать tmp_path для `project_root` и предзаписанный .swax/config.yml:

```python
def test_run_discover_builds_graph(tmp_path, mocker):
    # подготовка .swax/config.yml в tmp_path
    # mock discover_specs, parse_spec, extract_paths возвращают фикстуры
    # mock build_llm_client и LLMClient.ask/ask_multi_turn возвращают JSON-ответы
    run_discover(project_root=tmp_path)
    assert (tmp_path / ".swax" / "traceability.yml").exists()
```

Не вызывать live LLM API в тестах — всегда mock.
