---
title: Installation
description: Install Swax from source with Python 3.10+.
---

# Installation

## Requirements

- Python **3.10** or newer.
- An LLM provider reachable over HTTP (Anthropic- or OpenAI-compatible API).

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # runtime
pip install -e '.[test]'    # + pytest, ruff (contributors)
pip install -e '.[docs]'    # + mkdocs (documentation site)
```

This installs the `swax` console script (`swax.cli.__main__:main`).

## Verify the install

```bash
swax --help
```

You should see the `init`, `discover`, and `plan` subcommands and the
`--env-file` global option.

## Next step

Continue to [Configuration](configuration.md) to set up `.env` and `.swax/config.yml`.
