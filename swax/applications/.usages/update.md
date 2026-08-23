# Update specs — use case for mirroring and conditional graph rebuild

## Domain

Invocation template for the non-interactive specs update use case. Target audience: cell
`commands/update/` (the CLI handler delegates to `run_update` after loading `.env`).

The use case orchestrates seven cells in one transaction: `config/` (read configuration),
`git/` (read-only clone), `fs/` (classification, staging, swap, path guard), `openapi/`
(parse + endpoint diff), `traceability/` (load/prune/persist), `prompts/` (incremental
rebuild prompts), `llm/` (one `ask` call in the incremental branch). Defensive JSON parsing
happens locally.

## Running the use case

`run_update` accepts only `project_root`; all other inputs come from `.swax/config.yml`:

```python
from pathlib import Path
from swax.applications.update import run_update

output = run_update(project_root=Path.cwd())
print(output)
```

Consumer conventions:
- Fully non-interactive — no prompts, no options.
- The project must be initialized — `.swax/config.yml` must exist and be valid.
- Returns the summary text; the caller (handler) is responsible for echoing it to stdout.
- Remote is the source of truth — local spec edits are overwritten silently.

## What runs inside

1. `load_config` — read `.swax/config.yml`.
2. `validate_specs_location` — refuse targets outside the project, the project root or its
   ancestor, and locations covering `.swax/`.
3. `clone_specs` (ctx-mgr) → `compare_specs` — byte-level file classification.
4. No changes → return "Specs are up to date." — graph untouched, no LLM needed.
5. Removals only → collect removed files' endpoints (old local content), minus the
   endpoints still declared by surviving specs → inside
   `staged_specs_swap`: graph file exists → `load_traceability` → `remove_paths` →
   `deduplicate` → atomic save, status "rebuilt"; graph file missing → specs applied,
   graph stays missing, no status line (no LLM in either case).
6. Added/updated → `require_vars` BEFORE applying specs; graph exists → incremental:
   endpoint diff per modified pair (with endpoints of removed spec files folded into the
   removed list — whole-file removals are pruned in the same revision) + added files'
   content → one `LLMClient.ask` → defensive parse → universe filter → atomic save.
   Status: "rebuilt".
7. Added/updated and no graph file → `run_discover` (full two-pass build). Status: "built".
8. Rebuild failure after the swap → specs restored from backup, `GraphRebuildFailedError`;
   when no graph file existed before the attempt, a partially written graph file is removed.

## Domain exception handling

`run_update` catches nothing except the rebuild block (rollback point →
`GraphRebuildFailedError`). Everything else propagates; the CLI handler maps:
`UnsafeSpecsLocationError`, `RepositoryCloneError`, `SpecsNotFoundError`,
`MissingEnvironmentVariablesError`, `SpecParseError`, LLM transport errors,
`GraphRebuildFailedError`. Raw config-reading failures propagate unwrapped.

## Testing

Mock domain routines at their import point; use `tmp_path` with a pre-written
`.swax/config.yml` and real spec trees. Cover failure injection per phase: before the swap
(config, clone, env validation), inside the rebuild (LLM/parse errors → specs restored),
at the graph write. Never call the live LLM API — always mock.
