# Swax

Swax is a tool for building **traceability graphs** of API endpoint dependencies
from OpenAPI / Swagger specifications, using a two-pass LLM analysis. Given a
spec repository, it infers which API paths depend on which other paths and
persists the result as a deterministic graph.

> Status: Alpha. The `init`, `discover`, `plan`, and `update` commands are the
> currently implemented surface.

📖 **Documentation:** https://qarium.github.io/swax/

## Requirements

- Python 3.10 or newer.
- An LLM provider reachable over HTTP (Anthropic- or OpenAI-compatible API).

## Installation

```bash
pipx install swax
```

For contributors, from a checkout:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'    # + pytest, ruff
pip install -e '.[docs]'    # + mkdocs (documentation site)
```

This installs the `swax` console script (`swax.cli.__main__:main`).

## Environment

Swax reads four environment variables for the LLM transport. Put them in a
`.env` file (loaded via the `--env-file` option) or export them in your shell —
shell values take precedence over the file:

| Variable | Meaning |
| --- | --- |
| `SWAX_LLM_MODEL` | Model name (e.g. `claude-sonnet-4-6`, `gpt-4o`). |
| `SWAX_LLM_PROTOCOL` | Provider identifier: `anthropic` or `openai`. |
| `SWAX_LLM_BASE_URL` | LLM API base URL (without a `/v1` or `/v2` version segment — the SDK appends it). |
| `SWAX_LLM_TOKEN` | LLM API token. Never written to logs or error messages. |

## Usage

```bash
swax --env-file .env init
swax --env-file .env discover
swax --env-file .env plan
swax --env-file .env update
```

`--env-file` defaults to `.env`; a missing file is silently ignored.

### `swax init`

Interactively prompts for:

1. Repository URL — the git source of the specifications.
2. Path to specs inside the repo — the subdirectory to copy.
3. Local download path — where the specs land in the project.

It writes `.swax/config.yml`, shallow-clones the repository (`depth=1`), and
copies the specs into the local download path. Failures exit with code 1 and a
readable message (`Failed to clone <url>: <reason>`, `Specs not found at <path>`).

### `swax discover`

Rebuilds `.swax/traceability.yml` from scratch (no prompts; reads
`.swax/config.yml` and the environment). It discovers and parses the local
specs, runs a two-pass LLM analysis (an initial dependency-graph pass, then a
schema-informed refine pass for the uncertain pairs), deduplicates the edges,
and overwrites the traceability graph. Domain failures map to exit code 1 with
messages such as `Missing env vars: ...`, `Failed to parse <path>: <reason>`,
`LLM rate limited; retry later`, `LLM call failed: <reason>`,
`Unsupported LLM protocol: <protocol>`, `LLM response parse failed: <reason>`.

### `swax plan`

Analyzes spec changes and prints a Markdown Impact Report to stdout (no prompts;
reads `.swax/config.yml`, the environment, and `.swax/traceability.yml` produced
by `swax discover`). It parses the local baseline specs, shallow-clones the spec
repository fresh, classifies the endpoint diff (added / removed / modified), maps
the changed endpoints onto the traceability graph to find transitively affected
endpoints, and runs a single-turn LLM analysis. With no changes it skips the LLM
and prints a `LOW`-risk "No changes detected" report. The report has Summary,
Risk (`HIGH` / `MEDIUM` / `LOW`), Modified Endpoints, Affected Endpoints,
Requirements, and Checklist sections. Domain failures map to exit code 1 with
messages such as `Missing env vars: ...`, `Failed to parse <path>: <reason>`,
`Failed to clone <url>: <reason>`, `Specs directory not found at <path>`,
`Traceability graph not found at <path> — run \`swax discover\` first`,
`LLM rate limited; retry later`, `LLM call failed: <reason>`,
`Unsupported LLM protocol: <protocol>`, `LLM response parse failed: <reason>`.

### `swax update`

Mirrors the local specs to the remote state and rebuilds the traceability
graph conditionally, as one transaction (no prompts; reads `.swax/config.yml`
and the environment). The command shallow-clones the spec repository fresh
and classifies the byte-level file diff, then branches:

- **No changes** — prints `Specs are up to date.` and touches nothing.
- **Removals only** — mirrors the specs and prunes the graph deterministically
  without an LLM call.
- **Added/updated files** — validates `SWAX_LLM_*` before any mutation, then
  revises the graph incrementally with a single LLM turn
  (`Traceability graph: rebuilt`) or builds it from scratch via the discover
  flow when no graph exists (`Traceability graph: built`).

The summary lists `Added:` / `Updated:` / `Removed:` groups plus the graph
status. The remote is the source of truth — local spec edits are overwritten;
a failed rebuild restores the previous specs and graph. Failures exit with
code 1 and messages such as
`Refusing to mirror into <path>`, `Graph rebuild failed: <reason>; specs
restored.`, `Failed to clone <url>: <reason>`, `Specs not found at <path>`,
`Missing env vars: ...`, `Failed to parse <path>: <reason>`,
`LLM rate limited; retry later`, `LLM call failed: <reason>`,
`Unsupported LLM protocol: <protocol>`, `LLM response parse failed: <reason>`.

## Project layout

```
.swax/
  config.yml          # written by `swax init`
  traceability.yml    # written by `swax discover`, pruned/rebuilt by `swax update`
<download_path>/      # the copied specifications (re-mirrored by `swax update`)
```

`.swax/config.yml` shape:

```yaml
git:
  url: https://example.com/specs.git
  location: specs
specs:
  type: openapi        # openapi | swagger
  location: downloaded
```

## Development

```bash
pytest                       # full suite
ruff check swax tests        # lint
ruff format --check swax tests
```

## License

BSD-3-Clause.
