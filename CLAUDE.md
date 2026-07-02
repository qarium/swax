# CLAUDE.md

Reference for AI agents working in this repository. Captures the non-obvious
conventions; authoritative rules live in `.goga/usages/conventions.md` and the
per-cell `CODEMANIFEST` files.

## Commands

```bash
pip install -e '.[test]'
pytest                              # full suite (contract + logic pairs per cell)
ruff check swax tests
ruff format --check swax tests
python -m swax.cli --help           # smoke-check the entry point
```

## Architecture: cells

`swax/` is organized into **cells** (leaf cells → facade cells → `cli`). Each
cell ships a `CODEMANIFEST` (entity/routine contracts) and a `.usages/` doc.

- **`CODEMANIFEST` and `.usages/` are read-only contracts.** If implementation
  and manifest disagree, fix the implementation — never the manifest.
- One entity per file; files are named after the entity
  (`Config.py`, `GitConfig.py`, `TraceabilityGraph.py`). This is the `location`
  contract. It is why `N999` (PascalCase module names) is disabled in
  `pyproject.toml` — do not "fix" the filenames.
- Relative imports inside a cell; absolute imports across cells
  (`from swax.config import ...`). See `.goga/usages/conventions.md`.

### Cell map

- `swax/config` — `Config`/`GitConfig`/`SpecsConfig` (pydantic), env loading
  (`load_env`, `require_vars`), `parse_protocol`/`parse_base_url`, config YAML
  storage.
- `swax/fs` — `ensure_swax_dir`, `copy_specs`.
- `swax/git` — `clone_specs` (contextmanager, shallow clone into a temp dir),
  `RepositoryCloneError`, `SpecsNotFoundError`.
- `swax/openapi` — `parse_spec` (Prance, full `$ref` dereference via
  `RESOLVE_ALL`), `extract_paths`, `extract_schemas`, `discover_specs`.
- `swax/traceability` — `TraceabilityGraph` (pydantic), `load_traceability`,
  `save_traceability` (deterministic, sorted YAML).
- `swax/prompts` — system/user/refine prompt builders.
- `swax/llm` — `LLMClient` protocol, `AnthropicAdapter`/`OpenAIAdapter`,
  `build_llm_client` factory, domain errors.
- `swax/applications` — use-cases `run_init`, `run_discover` (facade re-exports
  `run_init_handler`/`run_discover_handler`).
- `swax/commands` — thin Click handlers `init`, `discover` (facade re-exports
  `init_handler`/`discover_handler`); map domain errors to `click.ClickException`.
- `swax/cli` — `main` group (`--env-file`), `SwaxContext` pass object.

### `cli` ↔ `commands` is acyclic on purpose

`init`/`discover` are registered **lazily in `swax/cli/__main__.py`**, never in
`swax/cli/__init__.py`. The command cells import `SwaxContext` only under
`TYPE_CHECKING`. This keeps the dependency edge acyclic (commands import from
`cli`, not the reverse). Do not move registration into `__init__.py`. As a
consequence, importing `swax.cli.main` alone does not register subcommands —
`swax.cli.__main__` must be imported (the entry point and the CLI tests do this).

## Conventions worth remembering

- **pydantic:** all models use `model_config = ConfigDict(kw_only=True)`. This
  is why `UP045` (`X | None`) is disabled — use `typing.Optional` for Python
  3.10 dataclass/field compatibility.
- **Deterministic YAML:** `save_config`/`save_traceability` dump with
  `sort_keys=False, allow_unicode=True, default_flow_style=False`;
  `save_traceability` additionally sorts keys and adjacency lists in Python so
  repeated writes are byte-identical.
- **Credential boundary:** `SWAX_LLM_TOKEN` must never appear in logs or in any
  exception/message string. Adapters store the SDK client (which owns the
  token); error `reason`s come from SDK exceptions, not the token.
- **`parse_protocol` / `parse_base_url`** are exported and unit-tested but are
  **not** called on the live path — they are reserved for a future eager
  validation decision. Do not wire them in without an explicit design change.

## Testing discipline

- Tests mirror `swax/` under `tests/`. Every coding task has a
  `*_contract.py` (facade/signature) and `*_logic.py` (behavior) pair.
- SDK/LLM/git-remote calls are mocked at their import/use site via
  `mocker.patch` — no live API or network. `tmp_path`, `monkeypatch`, and
  `mocker` (pytest-mock) are the fixtures.
- LLM transport is patched as
  `swax.applications.discover.run_discover.build_llm_client`; adapters receive
  an injected SDK client for testability.
