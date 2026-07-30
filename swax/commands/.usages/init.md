# Init command — Click handler for the `init` command

## Domain

Registration and invocation template for the `init` Click command. Target audience: cell `swax/cli/` (registers the command on the `main` group via `main.add_command(init)`).

The command is thin — only interactive prompts and error mapping. Application logic (cloning, copying, writing configuration) is delegated to `run_init` (cell `applications/init/`).

---

## Command registration

`init` is a decorated `@click.command` callback. Registration on the main group:

```python
from swax.cli import main
from swax.commands.init import init

main.add_command(init)
```

Consumer conventions:
- The command takes no CLI options — all inputs are collected via interactive prompts.
- The context is passed via `@click.pass_obj` — `SwaxContext` from the `cli/` cell.

---

## Command execution

On `swax init`, the command:

1. Receives `SwaxContext` via `@click.pass_obj`.
2. Prompts for `repo_url`, `specs_location`, `download_path` via `click.prompt`.
3. Resolves `project_root = pathlib.Path.cwd()`.
4. Delegates to `run_init(repo_url, specs_location, download_path, project_root)`.
5. Catches `RepositoryCloneError` / `SpecsNotFoundError` and maps them to `click.ClickException`.

---

## Error handling

Domain exceptions from `git/` are mapped to `click.ClickException` for uniform exit codes:

- RepositoryCloneError -> click.ClickException(f"Failed to clone {exc.url}: {exc.reason}")
- SpecsNotFoundError -> click.ClickException(f"Specs not found at {exc.path}")

Exit codes: 0 — success, 1 — failure (Click default for `ClickException`).

---

## Testing

Test via `click.testing.CliRunner`, invoking the callback directly without a subprocess:

```python
from click.testing import CliRunner
from swax.commands.init import init


def test_init_prompts_and_delegates(mocker):
    mocker.patch("swax.commands.init.run_init")
    runner = CliRunner()
    result = runner.invoke(init, input="https://example.com/repo.git\nspecs/\n./local_specs\n")
    assert result.exit_code == 0
```

In tests, mock `run_init` at its import point — do not perform a real clone.
