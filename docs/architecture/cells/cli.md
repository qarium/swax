---
title: swax/cli
description: CLI entry point — Click group with --env-file, SwaxContext pass object.
---

# `swax/cli`

CLI entry point. The top-level Click group loads the environment and
initializes a `SwaxContext` for subcommands. Subcommands `init`, `discover`,
`plan`, and `update` are registered **lazily** in `__main__.py` to keep the
CODEMANIFEST contract acyclic (`commands` import from `cli`, not the reverse).

`main` and `SwaxContext` are exported as the cell's public API.

## Public API

### `main(ctx: click.Context, env_file: pathlib.Path)`

Top-level Click group with the `--env-file` option: loads the environment and
initializes `SwaxContext` for subcommands.

- `ctx`: Click context object holding the `SwaxContext`.
- `env_file`: path to the environment file (default `.env`).

Algorithm:

1. Decorate with `@click.group` and the `--env-file` option (default `.env`).
2. Decorate the callback with `@click.pass_context`.
3. Call `load_env` with the resolved `env_file`.
4. Set `ctx.obj` to a new `SwaxContext`.

Requirements:

- Registered as `swax = "swax.cli.__main__:main"` in `[project.scripts]`.
- Subcommands are registered in `__main__.py`, not in the group callback.

Constraints:

- Does **not** raise on a missing `.env` — `load_env` handles it.
- Does **not** read `SWAX_*` variables here — validation happens lazily inside
  subcommands.

### `SwaxContext(env_file: pathlib.Path)`

Click pass object carrying CLI parameters between `main` and its subcommands.

- `env_file`: path to the environment file, passed via `--env-file`.

Properties:

| Property | Type | Description |
| --- | --- | --- |
| `env_file` | `pathlib.Path` | Path to the environment file. Read-only after construction — passed as input to `load_env`. |
| `config` | `Config \| None` | Cached project configuration, defaults to `None`. Subcommands may populate it lazily via `load_config`; optional because `init` writes config rather than reading it. |

## Subcommand registration pattern

The `init`, `discover`, `plan`, and `update` subcommands are registered on
the `main` group via `main.add_command()`. To avoid circular imports between
`cli/` and `commands/`, registration is performed lazily in `__main__.py`:

```python
# swax/cli/__main__.py
from swax.cli import main
from swax.commands import discover_handler, init_handler, plan_handler, update_handler

main.add_command(init_handler, name="init")
main.add_command(discover_handler, name="discover")
main.add_command(plan_handler, name="plan")
main.add_command(update_handler, name="update")

if __name__ == "__main__":
    main()
```

Commands are imported only in `__main__.py`, **not** in `__init__.py` — this
keeps the CODEMANIFEST contract cycle-free.

## Using `SwaxContext` in a subcommand

Subcommands receive `SwaxContext` via `@click.pass_obj`:

```python
import click
from swax.cli import SwaxContext

@click.command()
@click.pass_obj
def my_command(ctx: SwaxContext) -> None:
    # ctx.env_file — already loaded by the main group callback
    # ctx.config    — None by default; load via load_config if needed
    pass
```

## See also

- [Commands](../../guide/commands.md) — end-user CLI surface.
- [Architecture / commands cell](commands.md) — subcommand handlers.
