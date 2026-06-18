# Click — CLI Framework

## Domain

Patterns for building the Swax CLI using Click 8.x. Target audience: cells that expose CLI command entry points (the `cli/` cell hierarchy).

Swax CLI follows the architecture rule: **Click is the only CLI framework** — no Typer, no FastAPI. Command handlers stay thin; application logic lives in domain/infra cells.

---

## CLI Entry Point

Define a top-level group as the package entry point. Register subcommands via decorators.

```python
import click


@click.group()
@click.option(
    "--env-file",
    type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
    default=".env",
    show_default=True,
    help="Path to the environment file.",
)
@click.pass_context
def main(ctx: click.Context, env_file: pathlib.Path) -> None:
    """Swax — API traceability graph builder."""
    ctx.ensure_object(dict)
    ctx.obj["env_file"] = env_file
```

Register commands on the group:

```python
@main.command()
def init() -> None:
    """Initialize a Swax project."""

@main.command()
def discover() -> None:
    """Rebuild the traceability graph from scratch."""
```

Wire the entry point in `pyproject.toml`:

```toml
[project.scripts]
swax = "swax.cli.__main__:main"
```

---

## Pass Object Pattern

Share state across nested commands with `click.pass_obj`:

```python
class SwaxContext:
    def __init__(self, env_file: pathlib.Path) -> None:
        self.env_file = env_file
        self.config: Optional[Config] = None


@main.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    ctx.obj = SwaxContext(ctx.params["env_file"])
```

---

## Interactive Prompts

Use `click.prompt` and `click.confirm` for the `init` command's interactive configuration. Validate input with the `value_proc` callback.

```python
@click.option("--repo-url", prompt="Repository URL", help="Git repo URL with specs.")
@click.option(
    "--specs-location",
    prompt="Path to specs inside the repo",
    help="Subdirectory in the repo containing OpenAPI specs.",
)
```

---

## Command Handler Discipline

Command handlers stay thin — orchestration only. Delegate to application services.

```python
@main.command()
@click.pass_obj
def init(ctx: SwaxContext) -> None:
    """Initialize a Swax project."""
    service = InitService(config_loader=ConfigLoader(env_file=ctx.env_file))
    service.run()
```

---

## Error Reporting

Convert application exceptions to Click errors using `click.ClickException`. This preserves consistent exit codes and user-facing messages.

```python
try:
    service.run()
except RepositoryNotFoundError as exc:
    raise click.ClickException(str(exc)) from exc
```

Exit codes: `0` for success, `1` for general failure (Click default for `ClickException`).

---

## Testing CLI Commands

Invoke command callbacks directly via `click.testing.CliRunner`. Do not spawn subprocesses in tests.

```python
from click.testing import CliRunner


def test_init_creates_config(tmp_path: pathlib.Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["init"], catch_exceptions=False)
    assert result.exit_code == 0
```