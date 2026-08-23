# CLI facade — entry point and pass object

## Domain

Usage templates for the Swax CLI entry point and the `SwaxContext` pass object. Target audience: the command cells `commands/init/`, `commands/discover/`, `commands/plan/`, and `commands/update/` (registered on the `main` group and reading `SwaxContext` via `@click.pass_obj`).

Click is the only CLI framework in Swax. The top-level `main` group with the `--env-file` option loads the environment before any subcommand runs.

---

## Subcommand registration

The `init`, `discover`, `plan`, and `update` subcommands are registered on the `main` group via `main.add_command()`. To avoid circular imports between `cli/` and `commands/`, registration is performed lazily in the `__main__.py` of the `cli/` cell:

```python
# swax/cli/__main__.py
from swax.cli import main

# Lazy registration — breaks the cli/ <-> commands/ cycle
from swax.commands.init import init
from swax.commands.discover import discover
from swax.commands.plan import plan
from swax.commands.update import update

main.add_command(init)
main.add_command(discover)
main.add_command(plan)
main.add_command(update)

if __name__ == "__main__":
    main()
```

Consumer conventions:
- `main` is the top-level Click group, decorated with `@click.group`.
- The `swax` entry-point script points to `swax.cli.__main__:main` in `[project.scripts]`.
- Commands are imported only in `__main__.py`, not in `__init__.py` — this keeps the CODEMANIFEST contract cycle-free.

---

## Using SwaxContext in a subcommand

Subcommands receive `SwaxContext` via `@click.pass_obj`. The context carries `env_file`; project configuration is loaded lazily:

```python
import click

from swax.cli import SwaxContext


@click.command()
@click.pass_obj
def my_command(ctx: SwaxContext) -> None:
    # ctx.env_file — path to .env, already loaded by the main group callback
    # ctx.config — None by default; load it via load_config if needed
    pass
```

Consumer conventions:
- `env_file` is read-only after construction; it has already been passed to `load_env` by the group callback.
- `config` is an optional configuration cache. The `init` command does not use it (it writes the configuration). The `discover` command loads configuration via `load_config` inside the use case, not through the context.

---

## The --env-file option

The end user passes `.env` via `--env-file`:

```bash
swax --env-file .env discover
swax --env-file /path/to/.env init
```

Default is `--env-file .env`. Environment variables already set in the shell take precedence over the file (`override=False` in `load_dotenv`).

---

## Testing

Test the entry point via `CliRunner`, passing a mock `SwaxContext` through `obj=`:

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

In tests, `load_env` may be mocked to avoid real writes to `os.environ`.
