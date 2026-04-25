# Development

Use a local Python environment for tests, docs builds, and packaging checks.
Keep downstream-specific behavior in downstream packages.

## Environment

The preferred local environment is a repo-local Conda environment at `./.conda`.

Create it when needed:

```sh
conda create -p ./.conda python=3.12
```

Install the package and development tools:

```sh
./.conda/bin/python -m pip install -e ".[dev]"
```

An equivalent virtual environment is acceptable, but use the same commands with
that environment's `python`, `pytest`, and `mkdocs` executables.

## Daily Commands

Run package tests:

```sh
./.conda/bin/python -m pytest tests -q
```

Build public docs strictly:

```sh
./.conda/bin/mkdocs build --strict
```

Build distribution artifacts:

```sh
./.conda/bin/python -m build
```

## Ownership

`pubify-data` owns shared runtime contracts, neutral result models, decorators,
discovery, data helpers, and reusable CLI composition.

Downstream packages own workspace schemas, executable names, renderer output,
generated artifact filenames, preview/build behavior, and format-specific
commands.
